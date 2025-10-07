# Generated migration for additional database indexes
# Adds indexes for frequently queried fields to improve query performance

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_testparameter_display_order'),
    ]

    operations = [
        # Sample model indexes
        migrations.AddIndex(
            model_name='sample',
            index=models.Index(fields=['date_received_at_lab'], name='sample_received_lab_idx'),
        ),
        migrations.AddIndex(
            model_name='sample',
            index=models.Index(fields=['current_status', 'date_received_at_lab'], name='sample_status_received_idx'),
        ),

        # TestResult model indexes
        migrations.AddIndex(
            model_name='testresult',
            index=models.Index(fields=['test_date'], name='testresult_date_idx'),
        ),
        migrations.AddIndex(
            model_name='testresult',
            index=models.Index(fields=['technician'], name='testresult_tech_idx'),
        ),
        migrations.AddIndex(
            model_name='testresult',
            index=models.Index(fields=['test_date', 'technician'], name='testresult_date_tech_idx'),
        ),

        # ConsultantReview model indexes
        migrations.AddIndex(
            model_name='consultantreview',
            index=models.Index(fields=['status'], name='review_status_idx'),
        ),
        migrations.AddIndex(
            model_name='consultantreview',
            index=models.Index(fields=['review_date'], name='review_date_idx'),
        ),
        migrations.AddIndex(
            model_name='consultantreview',
            index=models.Index(fields=['status', 'review_date'], name='review_status_date_idx'),
        ),
        migrations.AddIndex(
            model_name='consultantreview',
            index=models.Index(fields=['reviewer', 'review_date'], name='review_reviewer_date_idx'),
        ),
    ]
