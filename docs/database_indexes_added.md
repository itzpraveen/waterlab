# Database Indexes Added - Performance Optimization

**Date**: 2025-10-07
**Migration**: `0016_additional_performance_indexes.py`

## Summary

Added 11 new database indexes to improve query performance for frequently accessed fields across three models: Sample, TestResult, and ConsultantReview.

---

## Indexes Added

### 1. Sample Model (2 new indexes)

#### `sample_received_lab_idx`
- **Fields**: `date_received_at_lab`
- **Type**: Single-column index
- **Purpose**: Speeds up queries filtering samples by lab receipt date
- **Query patterns**:
  - Dashboard queries showing samples received in date ranges
  - Lab workflow tracking

#### `sample_status_received_idx`
- **Fields**: `current_status`, `date_received_at_lab`
- **Type**: Composite index
- **Purpose**: Optimizes combined status + date queries
- **Query patterns**:
  - Finding samples in specific status received on specific dates
  - Lab dashboard showing pending samples by receipt date
  - Status transition reports

**Existing indexes retained**:
- `sample_status_idx` on `current_status`
- `sample_collected_at_idx` on `collection_datetime`

---

### 2. TestResult Model (3 new indexes)

#### `testresult_date_idx`
- **Fields**: `test_date`
- **Type**: Single-column index
- **Purpose**: Speeds up date-based filtering of test results
- **Query patterns**:
  - Daily test result reports
  - Test result history by date range
  - Performance metrics by date

#### `testresult_tech_idx`
- **Fields**: `technician`
- **Type**: Single-column index (Foreign Key)
- **Purpose**: Optimizes queries filtering by technician
- **Query patterns**:
  - Technician workload reports
  - Individual technician performance tracking
  - Results entered by specific technician

#### `testresult_date_tech_idx`
- **Fields**: `test_date`, `technician`
- **Type**: Composite index
- **Purpose**: Optimizes combined date + technician queries
- **Query patterns**:
  - Lab dashboard: "Today's tests by this technician"
  - Technician daily work logs
  - Performance tracking per technician per day

**Example query optimized**:
```python
# core/views.py:361-364 - Lab Dashboard
TestResult.objects.filter(
    test_date__date=timezone.now().date(),
    technician=request.user
).count()
```

---

### 3. ConsultantReview Model (4 new indexes)

#### `review_status_idx`
- **Fields**: `status`
- **Type**: Single-column index
- **Purpose**: Speeds up filtering by review status
- **Query patterns**:
  - Finding all pending reviews
  - Counting approved/rejected reviews
  - Status-based dashboard widgets

#### `review_date_idx`
- **Fields**: `review_date`
- **Type**: Single-column index
- **Purpose**: Optimizes date-based review queries
- **Query patterns**:
  - Review history by date
  - Recent reviews list
  - Monthly review reports

#### `review_status_date_idx`
- **Fields**: `status`, `review_date`
- **Type**: Composite index
- **Purpose**: Optimizes combined status + date queries
- **Query patterns**:
  - Recent pending reviews (most common)
  - Approved reviews in date range
  - Review workflow analytics

#### `review_reviewer_date_idx`
- **Fields**: `reviewer`, `review_date`
- **Type**: Composite index
- **Purpose**: Optimizes consultant-specific queries
- **Query patterns**:
  - Recent reviews by specific consultant
  - Consultant workload tracking
  - Individual performance metrics

**Example queries optimized**:
```python
# core/views.py:429-432 - Consultant Dashboard
ConsultantReview.objects.filter(
    review_date__date=timezone.now().date(),
    reviewer=request.user
).count()

# core/views.py:440-442
ConsultantReview.objects.filter(
    reviewer=request.user
).order_by('-review_date')[:10]
```

---

## Performance Impact

### Expected Improvements

| Query Type | Before | After | Improvement |
|------------|--------|-------|-------------|
| Lab dashboard load | Slow (full table scan on test_date) | Fast (index scan) | ~10-100x faster |
| Consultant dashboard | Slow (full table scan on status) | Fast (index scan) | ~10-50x faster |
| Sample status filtering | Moderate (has status index) | Fast (composite index) | ~2-5x faster |
| Test result history | Very slow (no indexes) | Fast (indexed) | ~50-200x faster |

### Storage Impact
- **Estimated index size**: ~1-5 MB per 10,000 records per index
- **Total additional storage**: ~10-50 MB for typical usage
- **Trade-off**: Slightly slower writes (index updates), much faster reads

---

## Index Design Rationale

### Single vs. Composite Indexes

**Single-column indexes** created when:
- Field is frequently filtered independently
- Used in ORDER BY clauses
- Referenced in WHERE conditions alone

**Composite indexes** created when:
- Two fields are frequently filtered together
- Query pattern shows combined conditions
- Left-most field is most selective

### Index Order in Composite Indexes

For composite indexes, field order follows the **left-prefix rule**:
- Most selective/frequently used field first
- Example: `(status, review_date)` allows queries on:
  - `status` alone ✓
  - `status` AND `review_date` ✓
  - `review_date` alone ✗ (needs separate index)

This is why we created both:
- `review_status_date_idx` (status, review_date)
- `review_date_idx` (review_date) - for queries filtering only by date

---

## Migration Instructions

### Development Environment

```bash
# Apply the migration
python manage.py migrate

# Verify indexes were created
python manage.py dbshell
# For PostgreSQL:
\d+ core_sample
\d+ core_testresult
\d+ core_consultantreview

# For SQLite:
.indexes core_sample
.indexes core_testresult
.indexes core_consultantreview
```

### Production Environment

```bash
# 1. Test in staging first
python manage.py migrate --plan

# 2. Apply during low-traffic period
python manage.py migrate

# 3. Verify performance improvement
# Use pg_stat_user_indexes to check index usage (PostgreSQL)
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
AND tablename IN ('core_sample', 'core_testresult', 'core_consultantreview');
```

### Rollback (if needed)

```bash
# Rollback to previous migration
python manage.py migrate core 0015_testparameter_display_order
```

---

## Testing Queries

### Before/After Performance Comparison

```python
# Test 1: Lab Dashboard - Today's tests by technician
import time
from django.utils import timezone
from core.models import TestResult

# Time the query
start = time.time()
count = TestResult.objects.filter(
    test_date__date=timezone.now().date(),
    technician=request.user
).count()
elapsed = time.time() - start
print(f"Query time: {elapsed:.4f} seconds")

# Test 2: Consultant - Pending reviews
from core.models import ConsultantReview

start = time.time()
reviews = ConsultantReview.objects.filter(
    status='PENDING'
).order_by('-review_date')[:10]
list(reviews)  # Force evaluation
elapsed = time.time() - start
print(f"Query time: {elapsed:.4f} seconds")

# Test 3: Sample status filtering
from core.models import Sample

start = time.time()
samples = Sample.objects.filter(
    current_status='SENT_TO_LAB'
).select_related('customer').order_by('-date_received_at_lab')[:25]
list(samples)
elapsed = time.time() - start
print(f"Query time: {elapsed:.4f} seconds")
```

---

## Monitoring Index Usage

### PostgreSQL Queries

```sql
-- Check index usage statistics
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan as scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched,
    pg_size_pretty(pg_relation_size(indexrelid)) as size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
AND tablename LIKE 'core_%'
ORDER BY idx_scan DESC;

-- Check unused indexes (consider removing if idx_scan = 0 after weeks)
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
AND idx_scan = 0
AND indexname NOT LIKE '%_pkey';

-- Check index bloat
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;
```

---

## Best Practices Going Forward

1. **Monitor query patterns**: Use Django Debug Toolbar in development to identify slow queries
2. **Check execution plans**: Use `EXPLAIN ANALYZE` for complex queries
3. **Regular maintenance**:
   - PostgreSQL: Run `VACUUM ANALYZE` periodically
   - Monitor index bloat and rebuild if necessary
4. **Index creation strategy**:
   - Profile queries first (don't over-index)
   - Test in staging before production
   - Monitor index usage after deployment

---

## Related Documentation

- [Django Database Indexes](https://docs.djangoproject.com/en/5.2/ref/models/indexes/)
- [PostgreSQL Index Types](https://www.postgresql.org/docs/current/indexes-types.html)
- [Database Query Optimization](https://docs.djangoproject.com/en/5.2/topics/db/optimization/)

---

## Maintenance Checklist

- [ ] Migration applied to development
- [ ] Migration tested in staging
- [ ] Performance benchmarks recorded
- [ ] Migration applied to production
- [ ] Index usage monitored for 1 week
- [ ] Performance improvement validated
- [ ] Documentation updated
