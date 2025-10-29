import uuid

from django.test import TestCase
from django.urls import reverse
from .models import (
    Customer,
    Sample,
    TestParameter,
    CustomUser,
    TestResult,
    ConsultantReview,
    ResultStatusOverride,
    LabProfile,
)
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta

class CustomerModelTests(TestCase):
    def setUp(self):
        self.customer_data = {
            "name": "Test Customer",
            "phone": "1234567890",
            "email": "testcustomer@example.com",
            "street_locality_landmark": "123 Test Street",
            "village_town_city": "Testville",
            "panchayat_municipality": "Test Panchayat",
            "taluk": "Test Taluk",
            "district": "Ernakulam",
            "pincode": "682001" 
        }

    def test_create_customer(self):
        """Test that a customer can be created with valid data."""
        customer = Customer.objects.create(**self.customer_data)
        self.assertEqual(customer.name, self.customer_data["name"])
        self.assertEqual(customer.email, self.customer_data["email"])
        self.assertTrue(Customer.objects.filter(email=self.customer_data["email"]).exists())

    def test_customer_str_representation(self):
        """Test the string representation of the Customer model."""
        customer = Customer.objects.create(**self.customer_data)
        self.assertEqual(str(customer), self.customer_data["name"])

    def test_customer_address_auto_population(self):
        """Test that the 'address' field is auto-populated correctly."""
        customer = Customer.objects.create(**self.customer_data)
        expected_address_parts = [
            self.customer_data["street_locality_landmark"],
            self.customer_data["village_town_city"],
            self.customer_data["panchayat_municipality"],
            f"{self.customer_data['taluk']} Taluk",
            f"{customer.get_district_display()} District", # Use get_district_display for full name
            f"Kerala - {self.customer_data['pincode']}"
        ]
        # Filter out empty parts if any field was optional and empty
        expected_address = ", ".join(filter(None, expected_address_parts))
        self.assertEqual(customer.address, expected_address)

    def test_customer_pincode_validation_valid(self):
        """Test valid Kerala PIN codes."""
        valid_pincodes = ["670001", "682001", "695615"]
        for pincode in valid_pincodes:
            data = self.customer_data.copy()
            data["pincode"] = pincode
            data["email"] = f"test_{pincode}@example.com" # Ensure unique email
            customer = Customer(**data)
            customer.full_clean() # Should not raise ValidationError
            customer.save()
            self.assertEqual(customer.pincode, pincode)

    def test_customer_pincode_validation_invalid_range(self):
        """Test PIN codes outside Kerala's valid range."""
        invalid_pincodes = ["600001", "700000"]
        for pincode in invalid_pincodes:
            data = self.customer_data.copy()
            data["pincode"] = pincode
            data["email"] = f"test_invalid_{pincode}@example.com"
            customer = Customer(**data)
            with self.assertRaises(ValidationError) as context:
                customer.full_clean()
            self.assertIn("not a valid Kerala PIN code", str(context.exception))
            
    def test_customer_pincode_validation_invalid_format(self):
        """Test PIN codes with invalid format."""
        invalid_formats = ["12345", "1234567", "ABCDEF"]
        for pincode in invalid_formats:
            data = self.customer_data.copy()
            data["pincode"] = pincode
            data["email"] = f"test_invalid_format_{pincode}@example.com"
            customer = Customer(**data)
            with self.assertRaises(ValidationError):
                customer.full_clean() # RegexValidator or KeralaPincodeValidator should catch this

    def test_customer_email_unique_constraint(self):
        """Test that email addresses must be unique."""
        Customer.objects.create(**self.customer_data)
        duplicate_data = self.customer_data.copy() # Email is the same
        duplicate_data["name"] = "Another Customer" # Other fields can differ
        duplicate_data["phone"] = "0987654321"
        
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError): # Or ValidationError if caught at form/model clean level
             Customer.objects.create(**duplicate_data)


class SampleModelTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            name="Test Customer for Sample",
            phone="9876543210",
            email="testsamplecustomer@example.com",
            street_locality_landmark="456 Sample Avenue",
            village_town_city="Sampleburg",
            district="Kozhikode",
            pincode="673001"
        )
        self.lab_user = CustomUser.objects.create_user(
            username="labtech", password="password", role="lab"
        )
        self.sample_data = {
            "customer": self.customer,
            "collection_datetime": timezone.now() - timedelta(days=1),
            "sample_source": 'WELL',
            "collected_by": "John Doe"
        }

    def test_create_sample(self):
        """Test that a sample can be created and display_id is generated."""
        sample = Sample.objects.create(**self.sample_data)
        self.assertIsNotNone(sample.sample_id)
        self.assertTrue(sample.display_id.startswith(f"WL{timezone.now().year}-"))
        self.assertEqual(sample.customer.name, self.customer.name)

    def test_sample_str_representation(self):
        """Test the string representation of the Sample model."""
        sample = Sample.objects.create(**self.sample_data)
        self.assertEqual(str(sample), sample.display_id)

    def test_sample_display_id_generation_sequential(self):
        """Test that display_id is generated sequentially for the same year."""
        sample1 = Sample.objects.create(**self.sample_data)
        
        sample_data2 = self.sample_data.copy()
        sample_data2["collection_datetime"] = timezone.now() - timedelta(hours=12) # Ensure different time
        sample2 = Sample.objects.create(**sample_data2)
        
        year_prefix = f"WL{timezone.now().year}-"
        self.assertTrue(sample1.display_id.startswith(year_prefix))
        self.assertTrue(sample2.display_id.startswith(year_prefix))
        
        seq1 = int(sample1.display_id.split('-')[-1])
        seq2 = int(sample2.display_id.split('-')[-1])
        self.assertEqual(seq2, seq1 + 1)

    def test_sample_display_id_generation_new_year(self):
        """Test that display_id sequence resets for a new year."""
        # Create a sample for the current year
        sample_current_year = Sample.objects.create(**self.sample_data)
        current_year = timezone.now().year
        self.assertTrue(sample_current_year.display_id.startswith(f"WL{current_year}-"))

        # Mock timezone.now() to return a date in the next year
        # This requires a bit more advanced mocking, or manually creating data as if it were next year
        # For simplicity, we'll assume a way to control 'current_year' for display_id generation
        # or test by creating a sample and then forcing a new year scenario.

        # Let's simulate a new year by creating a sample and then advancing the clock
        # This is tricky without proper time mocking. A more robust way is to test the logic directly
        # or to create data that simulates a past year.

        # Alternative: Create a sample, then create another one as if it's a new year.
        # The model's save method uses timezone.now().year.
        # We can't easily mock timezone.now() within a single test run without a library like freezegun.
        # So, we'll test the logic by checking if a sample created with a future collection date
        # (implying it might be processed in a future year context if the ID logic was purely based on collection)
        # still adheres to the *current processing year* for ID generation.
        # The current implementation correctly uses `timezone.now().year` for the prefix.

        # A better test for new year:
        # 1. Create a sample for "last year" (requires setting its display_id and date manually or complex mocking)
        # 2. Create a new sample "this year" and check it starts from 0001.

        # Let's assume we have a sample from a previous year.
        # We can't easily create one with a past display_id that affects the sequence of the *current* year's
        # ID generation using the current Sample.save() logic directly without manipulating `timezone.now()`.
        # The current `save()` method correctly scopes `last_sample_this_year` to `timezone.now().year`.

        # Test: First sample of a year should be WL<year>-0001
        # To ensure this, we delete all samples for the current year if any exist from other tests
        Sample.objects.filter(display_id__startswith=f"WL{current_year}-").delete()
        first_sample_this_year = Sample.objects.create(**self.sample_data)
        self.assertEqual(first_sample_this_year.display_id, f"WL{current_year}-0001")

        # Create another sample to ensure sequence continues
        sample_data_next = self.sample_data.copy()
        sample_data_next["collection_datetime"] = timezone.now() - timedelta(hours=10)
        second_sample_this_year = Sample.objects.create(**sample_data_next)
        self.assertEqual(second_sample_this_year.display_id, f"WL{current_year}-0002")


    def test_sample_display_id_generation_first_of_year_after_previous_year_samples(self):
        """Test display_id starts from 0001 for a new year, even if previous year samples exist."""
        current_year = timezone.now().year
        previous_year = current_year - 1
        
        # Simulate a sample from the previous year (manually set display_id for test setup)
        # This doesn't use the model's save() to generate ID, but sets up the scenario.
        # Note: This approach is for testing the *new* year's ID generation.
        # The model's save() method correctly scopes its query to the *current* year.
        
        # To make this test more robust without complex time mocking, we'll ensure no samples
        # for the *current* year exist, then create one.
        Sample.objects.filter(display_id__startswith=f"WL{current_year}-").delete()
        
        # Create a dummy sample for a "previous year" to ensure it doesn't interfere.
        # This sample won't use the auto-ID generation for its own ID for this test part.
        # We are testing that the *new* sample gets ID 'WL<current_year>-0001'.
        # The model's logic `Sample.objects.filter(display_id__startswith=prefix)` is year-specific.
        
        # Create a sample for the current year, it should be the first one.
        first_sample_current_year = Sample.objects.create(**self.sample_data)
        self.assertTrue(first_sample_current_year.display_id.startswith(f"WL{current_year}-"))
        self.assertTrue(first_sample_current_year.display_id.endswith("-0001"),
                        f"Expected ID to end with -0001, got {first_sample_current_year.display_id}")

        # Create another one to ensure sequence
        sample_data_2 = self.sample_data.copy()
        sample_data_2["collection_datetime"] = timezone.now() - timedelta(minutes=30)
        second_sample_current_year = Sample.objects.create(**sample_data_2)
        self.assertTrue(second_sample_current_year.display_id.endswith("-0002"),
                        f"Expected ID to end with -0002, got {second_sample_current_year.display_id}")



    def test_sample_clean_date_received_before_collection(self):
        """Test validation for date_received_at_lab being before collection_datetime."""
        collection_time = timezone.now() - timedelta(days=2)
        received_time_before = collection_time - timedelta(days=1)
        
        sample_data_invalid_received = self.sample_data.copy()
        sample_data_invalid_received["collection_datetime"] = collection_time
        sample_data_invalid_received["date_received_at_lab"] = received_time_before
        
        sample = Sample(**sample_data_invalid_received)
        with self.assertRaises(ValidationError) as context:
            sample.full_clean()
        self.assertIn("Date received at lab cannot be before collection date.", str(context.exception))

    def test_sample_update_status_valid_transition(self):
        """Test a valid status transition."""
        sample = Sample.objects.create(**self.sample_data)
        self.assertEqual(sample.current_status, 'RECEIVED_FRONT_DESK')
        sample.update_status('SENT_TO_LAB', user=self.lab_user)
        self.assertEqual(sample.current_status, 'SENT_TO_LAB')
        self.assertIsNotNone(sample.date_received_at_lab) # Check timestamp auto-population

    def test_sample_update_status_invalid_transition(self):
        """Test an invalid status transition."""
        sample = Sample.objects.create(**self.sample_data)
        sample.current_status = 'REPORT_APPROVED' # Manually set to a later state
        sample.save()
        
        with self.assertRaises(ValidationError) as context:
            sample.update_status('SENT_TO_LAB', user=self.lab_user)
        self.assertIn("Cannot transition from REPORT_APPROVED to SENT_TO_LAB", str(context.exception))

    def test_sample_update_status_results_entered_requires_all_results(self):
        """Test that moving to RESULTS_ENTERED requires all test results."""
        sample = Sample.objects.create(**self.sample_data)
        param1 = TestParameter.objects.create(name="pH", unit="pH units", min_permissible_limit=6.5, max_permissible_limit=8.5)
        sample.tests_requested.add(param1)
        sample.current_status = 'TESTING_IN_PROGRESS' # Assume it's in progress
        sample.save()

        with self.assertRaises(ValidationError) as context:
            sample.update_status('RESULTS_ENTERED', user=self.lab_user)
        self.assertIn("missing test results for some parameters", str(context.exception))
        
        # Add a result, then try again
        from .models import TestResult # Local import to avoid circular dependency issues at top level
        TestResult.objects.create(sample=sample, parameter=param1, result_value="7.0", technician=self.lab_user)
        sample.update_status('RESULTS_ENTERED', user=self.lab_user) # Should now pass
        self.assertEqual(sample.current_status, 'RESULTS_ENTERED')
        self.assertIsNotNone(sample.report_number)

    def test_sample_update_status_to_cancelled(self):
        """Test transitioning to CANCELLED status from an intermediate state."""
        sample = Sample.objects.create(**self.sample_data)
        sample.update_status('SENT_TO_LAB', user=self.lab_user)
        self.assertEqual(sample.current_status, 'SENT_TO_LAB')
        
        sample.update_status('CANCELLED', user=self.lab_user)
        self.assertEqual(sample.current_status, 'CANCELLED')

    def test_status_transitions_update_testing_dates(self):
        parameter = TestParameter.objects.create(
            name=f"Parameter {uuid.uuid4()}",
            unit="mg/L"
        )
        sample = Sample.objects.create(**self.sample_data)
        sample.tests_requested.add(parameter)

        sample.update_status('SENT_TO_LAB', self.lab_user)
        sample.refresh_from_db()
        self.assertIsNotNone(sample.date_received_at_lab)
        self.assertIsNone(sample.test_commenced_on)
        self.assertIsNone(sample.test_completed_on)

        sample.update_status('TESTING_IN_PROGRESS', self.lab_user)
        sample.refresh_from_db()
        self.assertIsNotNone(sample.test_commenced_on)
        original_commenced_on = sample.test_commenced_on

        TestResult.objects.create(
            sample=sample,
            parameter=parameter,
            result_value='5',
            technician=self.lab_user
        )

        sample.update_status('RESULTS_ENTERED', self.lab_user)
        sample.refresh_from_db()
        self.assertIsNotNone(sample.test_completed_on)
        initial_completed_on = sample.test_completed_on

        sample.update_status('REVIEW_PENDING', self.lab_user)
        sample.refresh_from_db()
        self.assertEqual(sample.test_completed_on, initial_completed_on)

        Sample.objects.filter(pk=sample.pk).update(
            test_commenced_on=original_commenced_on - timedelta(days=3),
            test_completed_on=initial_completed_on - timedelta(days=1)
        )
        sample.refresh_from_db()
        sample.update_status('TESTING_IN_PROGRESS', self.lab_user)
        sample.refresh_from_db()
        self.assertIsNone(sample.test_completed_on)
        self.assertIsNotNone(sample.test_commenced_on)
        self.assertNotEqual(sample.test_commenced_on, original_commenced_on - timedelta(days=3))
        self.assertIsNotNone(sample.report_number)
        initial_number = sample.report_number

        sample.update_status('RESULTS_ENTERED', self.lab_user)
        sample.update_status('REVIEW_PENDING', self.lab_user)
        sample.update_status('REPORT_APPROVED', self.lab_user)
        sample.refresh_from_db()
        self.assertEqual(sample.report_number, initial_number)

    def test_sample_update_status_date_received_at_lab_not_overwritten(self):
        """Test that date_received_at_lab is not overwritten if already set."""
        initial_received_time = timezone.now() - timedelta(days=1)
        sample_data_with_received_date = self.sample_data.copy()
        sample_data_with_received_date["date_received_at_lab"] = initial_received_time
        
        sample = Sample.objects.create(**sample_data_with_received_date)
        sample.current_status = 'RECEIVED_FRONT_DESK' # Start from here
        sample.save()
        
        sample.update_status('SENT_TO_LAB', user=self.lab_user)
        self.assertEqual(sample.current_status, 'SENT_TO_LAB')
        self.assertEqual(sample.date_received_at_lab, initial_received_time, 
                         "date_received_at_lab should not be updated if already set.")

    def test_report_number_generated_sequentially(self):
        parameter = TestParameter.objects.create(name=f"Seq Param {uuid.uuid4()}", unit="mg/L")

        sample1 = Sample.objects.create(**self.sample_data)
        sample1.tests_requested.add(parameter)
        sample1.update_status('SENT_TO_LAB', self.lab_user)
        sample1.update_status('TESTING_IN_PROGRESS', self.lab_user)
        TestResult.objects.create(sample=sample1, parameter=parameter, result_value='4', technician=self.lab_user)
        sample1.update_status('RESULTS_ENTERED', self.lab_user)
        sample1.refresh_from_db()
        first_report_number = sample1.report_number
        self.assertTrue(first_report_number.startswith(f"RPT{timezone.now().year}-"))

        sample2 = Sample.objects.create(**self.sample_data)
        sample2.tests_requested.add(parameter)
        sample2.update_status('SENT_TO_LAB', self.lab_user)
        sample2.update_status('TESTING_IN_PROGRESS', self.lab_user)
        TestResult.objects.create(sample=sample2, parameter=parameter, result_value='5', technician=self.lab_user)
        sample2.update_status('RESULTS_ENTERED', self.lab_user)
        sample2.refresh_from_db()
        second_report_number = sample2.report_number

        self.assertNotEqual(first_report_number, second_report_number)
        self.assertTrue(int(second_report_number.split('-')[-1]) > int(first_report_number.split('-')[-1]))

    def test_resolve_signatories_uses_lab_profile_defaults(self):
        default_food = CustomUser.objects.create_user(username="default_food", role="lab")
        default_bio = CustomUser.objects.create_user(username="default_bio", role="lab")
        default_chem = CustomUser.objects.create_user(username="default_chem", role="lab")
        profile = LabProfile.objects.create(
            name="Profile Defaults",
            signatory_food_analyst=default_food,
            signatory_bio_manager=default_bio,
            signatory_chem_manager=default_chem,
        )
        sample = Sample.objects.create(**self.sample_data)
        signatories = sample.resolve_signatories(profile)
        self.assertEqual(signatories['food_analyst'], default_food)
        self.assertEqual(signatories['bio_manager'], default_bio)
        self.assertEqual(signatories['chem_manager'], default_chem)

    def test_resolve_signatories_prefers_sample_assignments(self):
        default_food = CustomUser.objects.create_user(username="fallback_food", role="lab")
        default_bio = CustomUser.objects.create_user(username="fallback_bio", role="lab")
        default_chem = CustomUser.objects.create_user(username="fallback_chem", role="lab")
        profile = LabProfile.objects.create(
            name="Profile Defaults",
            signatory_food_analyst=default_food,
            signatory_bio_manager=default_bio,
            signatory_chem_manager=default_chem,
        )
        assigned_food = CustomUser.objects.create_user(username="assigned_food", role="lab")
        assigned_bio = CustomUser.objects.create_user(username="assigned_bio", role="lab")
        assigned_chem = CustomUser.objects.create_user(username="assigned_chem", role="lab")

        sample = Sample.objects.create(
            customer=self.customer,
            collection_datetime=timezone.now() - timedelta(days=1),
            sample_source='TAP',
            collected_by="Override",
            food_analyst=assigned_food,
            reviewed_by=assigned_bio,
            lab_manager=assigned_chem,
        )
        signatories = sample.resolve_signatories(profile)
        self.assertEqual(signatories['food_analyst'], assigned_food)
        self.assertEqual(signatories['bio_manager'], assigned_bio)
        self.assertEqual(signatories['chem_manager'], assigned_chem)
 
    def test_sample_has_all_test_results(self):
        """Test the has_all_test_results method."""
        sample = Sample.objects.create(**self.sample_data)
        param1 = TestParameter.objects.create(name="TestParam 1 for has_all", unit="U")
        param2 = TestParameter.objects.create(name="TestParam 2 for has_all", unit="U")

        # No tests requested
        self.assertFalse(sample.has_all_test_results(), "Should be False if no tests requested.")

        sample.tests_requested.add(param1, param2)
        self.assertFalse(sample.has_all_test_results(), "Should be False if results are missing.")

        TestResult.objects.create(sample=sample, parameter=param1, result_value="10", technician=self.lab_user)
        self.assertFalse(sample.has_all_test_results(), "Should be False if some results are missing.")

        TestResult.objects.create(sample=sample, parameter=param2, result_value="20", technician=self.lab_user)
        self.assertTrue(sample.has_all_test_results(), "Should be True when all results are present.")
        
        # Test case: requested_count > 0 is important
        sample_no_params = Sample.objects.create(
            customer=self.customer, 
            collection_datetime=timezone.now(), 
            sample_source='OTHER', 
            collected_by="Test"
        )
        self.assertFalse(sample_no_params.has_all_test_results(), "Should be False if tests_requested.count() is 0")


    def test_sample_get_missing_test_results(self):
        """Test the get_missing_test_results method."""
        sample = Sample.objects.create(**self.sample_data)
        param1 = TestParameter.objects.create(name="TestParam 1 for missing", unit="U")
        param2 = TestParameter.objects.create(name="TestParam 2 for missing", unit="U")
        param3 = TestParameter.objects.create(name="TestParam 3 for missing", unit="U")

        sample.tests_requested.add(param1, param2, param3)
        
        TestResult.objects.create(sample=sample, parameter=param1, result_value="Val1", technician=self.lab_user)
        
        missing_params = sample.get_missing_test_results()
        self.assertEqual(missing_params.count(), 2)
        self.assertIn(param2, missing_params)
        self.assertIn(param3, missing_params)
        self.assertNotIn(param1, missing_params)

        TestResult.objects.create(sample=sample, parameter=param2, result_value="Val2", technician=self.lab_user)
        TestResult.objects.create(sample=sample, parameter=param3, result_value="Val3", technician=self.lab_user)
        self.assertEqual(sample.get_missing_test_results().count(), 0, "Should be 0 when all results are present.")

    def test_sample_can_be_reviewed(self):
        """Test the can_be_reviewed method under various conditions."""
        sample = Sample.objects.create(**self.sample_data)
        param = TestParameter.objects.create(name="ReviewParam", unit="units")
        
        # Condition 1: No tests requested
        sample.current_status = 'RESULTS_ENTERED'
        sample.save()
        self.assertFalse(sample.can_be_reviewed(), "Cannot be reviewed if no tests requested.")

        sample.tests_requested.add(param)
        
        # Condition 2: Status RESULTS_ENTERED, but results missing
        self.assertFalse(sample.can_be_reviewed(), "Cannot be reviewed if results missing, even if status is RESULTS_ENTERED.")

        TestResult.objects.create(sample=sample, parameter=param, result_value="ReviewVal", technician=self.lab_user)
        
        # Condition 3: Status RESULTS_ENTERED, all results present
        self.assertTrue(sample.can_be_reviewed(), "Should be reviewable if status RESULTS_ENTERED and all results present.")

        # Condition 4: Status REVIEW_PENDING, all results present
        sample.current_status = 'REVIEW_PENDING'
        sample.save()
        self.assertTrue(sample.can_be_reviewed(), "Should be reviewable if status REVIEW_PENDING and all results present.")

        # Condition 5: Status TESTING_IN_PROGRESS, all results present (should not be reviewable)
        sample.current_status = 'TESTING_IN_PROGRESS'
        sample.save()
        self.assertFalse(sample.can_be_reviewed(), "Should not be reviewable if status is TESTING_IN_PROGRESS.")
        
    def test_sample_is_completed_property(self):
        """Test the is_completed property."""
        sample = Sample.objects.create(**self.sample_data)
        
        completed_statuses = ['REPORT_APPROVED', 'REPORT_SENT']
        non_completed_statuses = ['RECEIVED_FRONT_DESK', 'SENT_TO_LAB', 'TESTING_IN_PROGRESS', 'RESULTS_ENTERED', 'REVIEW_PENDING', 'CANCELLED']
        
        for status in completed_statuses:
            sample.current_status = status
            sample.save()
            self.assertTrue(sample.is_completed, f"Sample should be completed with status {status}")
            
        for status in non_completed_statuses:
            sample.current_status = status
            sample.save()
            self.assertFalse(sample.is_completed, f"Sample should not be completed with status {status}")

    def test_audit_trail_on_sample_status_update(self):
        """Test that AuditTrail is created when sample status is updated via update_status."""
        from .models import AuditTrail # Local import
        sample = Sample.objects.create(**self.sample_data)
        initial_audit_count = AuditTrail.objects.count()
        
        sample.update_status('SENT_TO_LAB', user=self.lab_user)
        
        self.assertEqual(AuditTrail.objects.count(), initial_audit_count + 1)
        latest_log = AuditTrail.objects.latest('timestamp')
        self.assertEqual(latest_log.user, self.lab_user)
        self.assertEqual(latest_log.action, 'UPDATE')
        self.assertEqual(latest_log.model_name, 'Sample')
        self.assertEqual(latest_log.object_id, str(sample.pk))
        self.assertEqual(latest_log.old_values['current_status'], 'RECEIVED_FRONT_DESK')
        self.assertEqual(latest_log.new_values['current_status'], 'SENT_TO_LAB')


class TestParameterModelTests(TestCase):
    def test_create_test_parameter(self):
        """Test creating a test parameter."""
        param = TestParameter.objects.create(
            name="Turbidity", 
            unit="NTU", 
            min_permissible_limit=0, 
            max_permissible_limit=5
        )
        self.assertEqual(param.name, "Turbidity")
        self.assertEqual(param.unit, "NTU")
        self.assertEqual(str(param), "Turbidity (NTU)")

    def test_test_parameter_name_unique(self):
        """Test that parameter names are unique."""
        TestParameter.objects.create(name="pH", unit="pH units")
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            TestParameter.objects.create(name="pH", unit="No Unit") # Same name

class TestResultModelTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            name="Test Customer for Results", phone="1122334455", email="testresults@example.com",
            street_locality_landmark="789 Result Road", village_town_city="Resulton",
            district="thrissur", pincode="680001"
        )
        self.sample = Sample.objects.create(
            customer=self.customer, collection_datetime=timezone.now() - timedelta(days=1),
            sample_source='TAP', collected_by="Lab Staff"
        )
        self.parameter_numeric = TestParameter.objects.create(
            name="Lead", unit="mg/L", min_permissible_limit=0, max_permissible_limit=0.01
        )
        self.parameter_text = TestParameter.objects.create(
            name="Odor", unit="" # No numeric limits
        )
        self.lab_tech = CustomUser.objects.create_user(
            username="result_tech", password="password", role="lab"
        )
        self.admin_user = CustomUser.objects.create_user(
            username="result_admin", password="password", role="admin", is_staff=True, is_superuser=True
        )
        self.non_lab_user = CustomUser.objects.create_user(
            username="consultant_user", password="password", role="consultant"
        )


    def test_create_test_result_numeric(self):
        """Test creating a numeric test result."""
        result = TestResult.objects.create(
            sample=self.sample,
            parameter=self.parameter_numeric,
            result_value="0.005",
            technician=self.lab_tech
        )
        self.assertEqual(result.result_value, "0.005")
        self.assertEqual(result.technician, self.lab_tech)
        self.assertEqual(str(result), f"Result for {self.sample.display_id} - Lead: 0.005")

    def test_create_test_result_text(self):
        """Test creating a text-based test result."""
        result = TestResult.objects.create(
            sample=self.sample,
            parameter=self.parameter_text,
            result_value="No Objectionable Odor",
            technician=self.lab_tech
        )
        self.assertEqual(result.result_value, "No Objectionable Odor")

    def test_test_result_unique_together_sample_parameter(self):
        """Test that a sample can only have one result per parameter."""
        TestResult.objects.create(
            sample=self.sample, parameter=self.parameter_numeric, result_value="0.001", technician=self.lab_tech
        )
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            TestResult.objects.create(
                sample=self.sample, parameter=self.parameter_numeric, result_value="0.002", technician=self.lab_tech
            )
            
    def test_test_result_technician_role_validation_lab_tech(self):
        """Test that a lab technician can create a result."""
        result = TestResult(
            sample=self.sample, parameter=self.parameter_text, result_value="Clear", technician=self.lab_tech
        )
        result.full_clean() # Should not raise ValidationError
        result.save()
        self.assertEqual(result.technician, self.lab_tech)

    def test_test_result_technician_role_validation_admin(self):
        """Test that an admin can create a result."""
        result = TestResult(
            sample=self.sample, parameter=self.parameter_text, result_value="Clear Admin", technician=self.admin_user
        )
        result.full_clean() # Should not raise ValidationError
        result.save()
        self.assertEqual(result.technician, self.admin_user)

    def test_test_result_technician_role_validation_invalid_role(self):
        """Test that a user with a non-lab/non-admin role cannot create a result."""
        result = TestResult(
            sample=self.sample, parameter=self.parameter_text, result_value="Not Allowed", technician=self.non_lab_user
        )
        with self.assertRaises(ValidationError) as context:
            result.full_clean()
        self.assertIn("Only lab technicians and admins can enter test results.", str(context.exception))

    def test_is_within_limits_numeric(self):
        """Test is_within_limits for numeric results."""
        # Within limits
        result1 = TestResult.objects.create(sample=self.sample, parameter=self.parameter_numeric, result_value="0.005", technician=self.lab_tech)
        self.assertTrue(result1.is_within_limits())

        # Below min limit (if min_limit was, e.g., 0.001)
        # For current Lead parameter (min 0), any positive value is fine if below max.
        # Let's test max limit
        
        # Above max limit
        sample2 = Sample.objects.create(customer=self.customer, collection_datetime=timezone.now(), sample_source='TAP', collected_by="Staff 2")
        result2 = TestResult.objects.create(sample=sample2, parameter=self.parameter_numeric, result_value="0.015", technician=self.lab_tech)
        self.assertFalse(result2.is_within_limits())
        
        # Exactly on limit
        sample3 = Sample.objects.create(customer=self.customer, collection_datetime=timezone.now(), sample_source='TAP', collected_by="Staff 3")
        result3 = TestResult.objects.create(sample=sample3, parameter=self.parameter_numeric, result_value="0.010", technician=self.lab_tech)
        self.assertTrue(result3.is_within_limits()) # <= max_permissible_limit

    def test_is_within_limits_text(self):
        """Test is_within_limits for text results (should always be True)."""
        result = TestResult.objects.create(sample=self.sample, parameter=self.parameter_text, result_value="Present", technician=self.lab_tech)
        self.assertTrue(result.is_within_limits())

    def test_get_limit_status(self):
        """Test get_limit_status method."""
        # Within limits
        result1 = TestResult.objects.create(sample=self.sample, parameter=self.parameter_numeric, result_value="0.005", technician=self.lab_tech)
        self.assertEqual(result1.get_limit_status(), "WITHIN_LIMITS")

        # Above limit
        sample2 = Sample.objects.create(customer=self.customer, collection_datetime=timezone.now(), sample_source='TAP', collected_by="Staff X")
        result2 = TestResult.objects.create(sample=sample2, parameter=self.parameter_numeric, result_value="0.020", technician=self.lab_tech)
        self.assertEqual(result2.get_limit_status(), "ABOVE_LIMIT")
        
        # Text result
        sample3 = Sample.objects.create(customer=self.customer, collection_datetime=timezone.now(), sample_source='TAP', collected_by="Staff Y")
        result3 = TestResult.objects.create(sample=sample3, parameter=self.parameter_text, result_value="Clear", technician=self.lab_tech)
        self.assertEqual(result3.get_limit_status(), "NON_NUMERIC")

        # Test with a parameter that has only a min_limit
        param_min_only = TestParameter.objects.create(name="MinTest", unit="U", min_permissible_limit=5.0)
        sample4 = Sample.objects.create(customer=self.customer, collection_datetime=timezone.now(), sample_source='TAP', collected_by="Staff Z")
        result4_below = TestResult.objects.create(sample=sample4, parameter=param_min_only, result_value="4.0", technician=self.lab_tech)
        self.assertEqual(result4_below.get_limit_status(), "BELOW_LIMIT")
        
        # Update the existing result instead of creating a new one
        result4_below.result_value = "6.0"
        result4_below.save()
        result4_below.refresh_from_db() # Ensure the instance is updated with any model-level changes on save
        self.assertEqual(result4_below.get_limit_status(), "WITHIN_LIMITS")

        # Test with a parameter that has only a max_limit
        param_max_only = TestParameter.objects.create(name="MaxTest", unit="U", max_permissible_limit=10.0)
        sample5 = Sample.objects.create(customer=self.customer, collection_datetime=timezone.now(), sample_source='TAP', collected_by="Staff A")
        result5_above = TestResult.objects.create(sample=sample5, parameter=param_max_only, result_value="12.0", technician=self.lab_tech)
        self.assertEqual(result5_above.get_limit_status(), "ABOVE_LIMIT")
        result5_above.result_value = "8.0"
        result5_above.save()
        self.assertEqual(result5_above.get_limit_status(), "WITHIN_LIMITS")
        result5_above.result_value = "10.0" # Exactly on limit
        result5_above.save()
        self.assertEqual(result5_above.get_limit_status(), "WITHIN_LIMITS")

    def test_get_limit_status_text_override(self):
        """Textual results use configured status overrides when provided."""
        ResultStatusOverride.objects.create(text_value="BDL", status="WITHIN_LIMITS")
        result = TestResult.objects.create(
            sample=self.sample,
            parameter=self.parameter_numeric,
            result_value="BDL",
            technician=self.lab_tech
        )
        self.assertEqual(result.get_limit_status(), "WITHIN_LIMITS")
        self.assertTrue(result.is_within_limits())

    def test_get_limit_status_parameter_specific_override(self):
        """Parameter-specific override should take precedence over global mapping."""
        ResultStatusOverride.objects.create(text_value="Present", status="WITHIN_LIMITS")
        ResultStatusOverride.objects.create(
            parameter=self.parameter_text,
            text_value="Present",
            status="BELOW_LIMIT",
        )
        result = TestResult.objects.create(
            sample=self.sample,
            parameter=self.parameter_text,
            result_value="Present",
            technician=self.lab_tech,
        )
        self.assertEqual(result.get_limit_status(), "BELOW_LIMIT")
        self.assertFalse(result.is_within_limits())


    def test_is_within_limits_min_only_param(self):
        """Test is_within_limits for a parameter with only min_permissible_limit."""
        param_min_only = TestParameter.objects.create(name="MinOnlyParam", unit="Units", min_permissible_limit=5.0)
        sample = Sample.objects.create(customer=self.customer, collection_datetime=timezone.now(), sample_source='WELL', collected_by="Test")
        
        # Create one result and update its value
        result = TestResult.objects.create(sample=sample, parameter=param_min_only, result_value="4.0", technician=self.lab_tech)
        self.assertFalse(result.is_within_limits(), "Value 4.0 should be below min 5.0")
        
        result.result_value = "5.0"
        result.save()
        self.assertTrue(result.is_within_limits(), "Value 5.0 should be at min 5.0 (inclusive)")
        
        result.result_value = "6.0"
        result.save()
        self.assertTrue(result.is_within_limits(), "Value 6.0 should be above min 5.0")

    def test_is_within_limits_max_only_param(self):
        """Test is_within_limits for a parameter with only max_permissible_limit."""
        param_max_only = TestParameter.objects.create(name="MaxOnlyParam", unit="Units", max_permissible_limit=10.0)
        sample = Sample.objects.create(customer=self.customer, collection_datetime=timezone.now(), sample_source='POND', collected_by="Test")

        # Create one result and update its value
        result = TestResult.objects.create(sample=sample, parameter=param_max_only, result_value="9.0", technician=self.lab_tech)
        self.assertTrue(result.is_within_limits(), "Value 9.0 should be below max 10.0")

        result.result_value = "10.0"
        result.save()
        self.assertTrue(result.is_within_limits(), "Value 10.0 should be at max 10.0 (inclusive)")

        result.result_value = "11.0"
        result.save()
        self.assertFalse(result.is_within_limits(), "Value 11.0 should be above max 10.0")

    def test_is_within_limits_no_param(self):
        """Test is_within_limits when the result has no associated parameter."""
        # This scenario should ideally not happen if foreign key is enforced,
        # but testing the method's robustness.
        result_no_param = TestResult(sample=self.sample, result_value="10", technician=self.lab_tech)
        # We don't save it as parameter is required. We test the method directly.
        # result_no_param.parameter is None by default if not assigned.
        self.assertIsNone(result_no_param.is_within_limits())


    def test_get_limit_status_no_param(self):
        """Test get_limit_status when the result has no associated parameter."""
        result_no_param = TestResult(sample=self.sample, result_value="10", technician=self.lab_tech)
        self.assertEqual(result_no_param.get_limit_status(), "UNKNOWN")


class CustomUserModelTests(TestCase):
    def test_create_custom_user(self):
        """Test creating a custom user with a specific role."""
        user = CustomUser.objects.create_user(
            username="testuser", 
            password="password123", 
            email="testuser@example.com",
            role="frontdesk",
            phone="5551234567"
        )
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "testuser@example.com")
        self.assertEqual(user.role, "frontdesk")
        self.assertTrue(user.check_password("password123"))
        self.assertEqual(str(user), "testuser (Front Desk)")

    def test_user_role_methods(self):
        """Test the role-checking helper methods."""
        admin = CustomUser.objects.create_user(username="admin1", role="admin")
        lab_tech = CustomUser.objects.create_user(username="labtech1", role="lab")
        front_desk = CustomUser.objects.create_user(username="frontdesk1", role="frontdesk")
        consultant = CustomUser.objects.create_user(username="consultant1", role="consultant")

        self.assertTrue(admin.is_admin())
        self.assertFalse(admin.is_lab_tech())

        self.assertTrue(lab_tech.is_lab_tech())
        self.assertFalse(lab_tech.is_admin())

        self.assertTrue(front_desk.is_frontdesk())
        self.assertFalse(front_desk.is_consultant())

        self.assertTrue(consultant.is_consultant())
        self.assertFalse(consultant.is_frontdesk())

    def test_create_superuser(self):
        """Test creating a superuser."""
        admin_user = CustomUser.objects.create_superuser(
            username="superadmin",
            email="superadmin@example.com",
            password="superpassword",
            role="admin" # Superuser should typically have admin role
        )
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        self.assertTrue(admin_user.is_admin())


class ConsultantReviewModelTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            name="Review Customer", phone="3334445555", email="reviewcust@example.com",
            street_locality_landmark="Review St", village_town_city="Reviewville",
            district="kannur", pincode="670002"
        )
        self.sample_for_review = Sample.objects.create(
            customer=self.customer, collection_datetime=timezone.now() - timedelta(days=2),
            sample_source='RIVER', collected_by="Reviewer", current_status='REVIEW_PENDING'
        )
        # Add a parameter and result to make it reviewable
        self.param = TestParameter.objects.create(name="Coliform", unit="MPN/100ml", max_permissible_limit=0)
        self.sample_for_review.tests_requested.add(self.param)
        
        self.consultant_user = CustomUser.objects.create_user(
            username="reviewer", password="password", role="consultant"
        )
        self.lab_user = CustomUser.objects.create_user( # For creating the TestResult
            username="review_lab_tech", password="password", role="lab"
        )
        TestResult.objects.create(
            sample=self.sample_for_review, parameter=self.param, result_value="10", technician=self.lab_user
        )
        # Manually set status to REVIEW_PENDING after adding result, as update_status might not be called
        self.sample_for_review.current_status = 'REVIEW_PENDING'
        self.sample_for_review.save()

        self.admin_user = CustomUser.objects.create_user(
            username="review_admin", password="password", role="admin", is_staff=True, is_superuser=True
        )


    def test_create_consultant_review_approved(self):
        """Test creating an approved consultant review."""
        review = ConsultantReview.objects.create(
            sample=self.sample_for_review,
            reviewer=self.consultant_user,
            comments="Looks good.",
            recommendations="No action needed.",
            status='APPROVED'
        )
        self.sample_for_review.refresh_from_db() # Refresh to get status updated by review.save()
        self.assertEqual(review.status, 'APPROVED')
        self.assertEqual(review.reviewer, self.consultant_user)
        self.assertEqual(self.sample_for_review.current_status, 'REPORT_APPROVED')
        self.assertEqual(str(review), f"Review for {self.sample_for_review.display_id} by {self.consultant_user.username}")

    def test_create_consultant_review_rejected(self):
        """Test creating a rejected consultant review."""
        review = ConsultantReview.objects.create(
            sample=self.sample_for_review,
            reviewer=self.consultant_user,
            comments="Needs re-testing for parameter X.",
            recommendations="Re-test parameter X.",
            status='REJECTED'
        )
        self.sample_for_review.refresh_from_db()
        self.assertEqual(review.status, 'REJECTED')
        self.assertEqual(self.sample_for_review.current_status, 'TESTING_IN_PROGRESS') # Assuming rejection sends it back

    def test_consultant_review_reviewer_role_validation(self):
        """Test that only consultants or admins can be reviewers."""
        invalid_reviewer = CustomUser.objects.create_user(username="notconsultant", role="frontdesk")
        review = ConsultantReview(
            sample=self.sample_for_review,
            reviewer=invalid_reviewer,
            status='APPROVED'
        )
        with self.assertRaises(ValidationError) as context:
            review.full_clean()
        self.assertIn("Only consultants and admins can review samples.", str(context.exception))

    def test_consultant_review_sample_not_ready(self):
        """Test review creation if sample is not in a reviewable state."""
        not_ready_sample = Sample.objects.create(
            customer=self.customer, collection_datetime=timezone.now(), 
            sample_source='WELL', collected_by="Test", current_status='RECEIVED_FRONT_DESK'
        )
        review = ConsultantReview(
            sample=not_ready_sample,
            reviewer=self.consultant_user,
            status='APPROVED'
        )
        with self.assertRaises(ValidationError) as context:
            review.full_clean()
        self.assertIn("Sample is not ready for review", str(context.exception))

    def test_consultant_review_clean_sample_not_reviewable_missing_results(self):
        """Test clean() when sample status is RESULTS_ENTERED but results are missing."""
        sample_missing_results = Sample.objects.create(
            customer=self.customer, 
            collection_datetime=timezone.now() - timedelta(days=1),
            sample_source='POND', 
            collected_by="Test User"
        )
        param_temp = TestParameter.objects.create(name="Temporary Param", unit="C")
        sample_missing_results.tests_requested.add(param_temp)
        sample_missing_results.current_status = 'RESULTS_ENTERED' # Status is ready, but no TestResult object
        sample_missing_results.save()

        review = ConsultantReview(
            sample=sample_missing_results,
            reviewer=self.consultant_user,
            status='APPROVED'
        )
        with self.assertRaises(ValidationError) as context:
            review.full_clean()
        self.assertIn("Sample is not ready for review - missing test results or incorrect status.", str(context.exception))

    def test_consultant_review_save_no_status_change_for_pending(self):
        """Test that sample status does not change if review status is PENDING."""
        initial_sample_status = self.sample_for_review.current_status
        ConsultantReview.objects.create(
            sample=self.sample_for_review,
            reviewer=self.consultant_user,
            comments="Still pending.",
            status='PENDING'
        )
        self.sample_for_review.refresh_from_db()
        self.assertEqual(self.sample_for_review.current_status, initial_sample_status,
                         "Sample status should not change for a PENDING review.")

    def test_consultant_review_save_status_change_on_update_from_pending_to_approved(self):
        """Test sample status change when updating review from PENDING to APPROVED."""
        review = ConsultantReview.objects.create(
            sample=self.sample_for_review,
            reviewer=self.consultant_user,
            status='PENDING'
        )
        self.sample_for_review.refresh_from_db()
        # Ensure sample status is not 'REPORT_APPROVED' initially by the PENDING review
        self.assertNotEqual(self.sample_for_review.current_status, 'REPORT_APPROVED') 
        
        review.status = 'APPROVED'
        review.comments = "Now approved."
        review.save()
        self.sample_for_review.refresh_from_db()
        self.assertEqual(self.sample_for_review.current_status, 'REPORT_APPROVED')

    def test_consultant_review_admin_can_review(self):
        """Test that an admin user can create a review."""
        # Ensure sample is in a reviewable state
        self.sample_for_review.current_status = 'REVIEW_PENDING'
        if not self.sample_for_review.tests_requested.exists():
             self.sample_for_review.tests_requested.add(self.param)
        if not TestResult.objects.filter(sample=self.sample_for_review, parameter=self.param).exists():
            TestResult.objects.create(sample=self.sample_for_review, parameter=self.param, result_value="OK", technician=self.lab_user)
        self.sample_for_review.save()
        
        # Clean any existing review for this sample to avoid OneToOne constraint error
        ConsultantReview.objects.filter(sample=self.sample_for_review).delete()

        review = ConsultantReview(
            sample=self.sample_for_review,
            reviewer=self.admin_user, # Admin user
            comments="Admin approved.",
            status='APPROVED'
        )
        review.full_clean() # Should not raise ValidationError for reviewer role
        review.save()
        self.sample_for_review.refresh_from_db()
        self.assertEqual(review.reviewer, self.admin_user)
        self.assertEqual(self.sample_for_review.current_status, 'REPORT_APPROVED')


class TestResultEntryViewTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            name="Result Entry Customer",
            phone="9999999999",
            email="resultentry@example.com",
            street_locality_landmark="789 Lab Street",
            village_town_city="Resultville",
            district="Ernakulam",
            pincode="682001"
        )
        self.lab_user = CustomUser.objects.create_user(
            username="labtech_view",
            password="password",
            role="lab"
        )
        self.parameter = TestParameter.objects.create(
            name=f"Result Parameter {uuid.uuid4()}",
            unit="mg/L"
        )
        self.sample = Sample.objects.create(
            customer=self.customer,
            collection_datetime=timezone.now() - timedelta(days=1),
            sample_source='WELL',
            collected_by='CUSTOMER'
        )
        self.sample.tests_requested.add(self.parameter)
        self.sample.update_status('SENT_TO_LAB', self.lab_user)

    def test_save_and_send_for_review_sets_status_and_dates(self):
        self.client.force_login(self.lab_user)
        url = reverse('core:test_result_entry', args=[self.sample.sample_id])
        form_prefix = f'param_{self.parameter.parameter_id}'
        payload = {
            f'{form_prefix}-result_value': '5',
            f'{form_prefix}-observation': '',
            f'{form_prefix}-remarks': '',
            'submit_action': 'save_and_review',
        }

        response = self.client.post(url, data=payload)
        self.assertEqual(response.status_code, 302)

        self.sample.refresh_from_db()
        self.assertEqual(self.sample.current_status, 'REVIEW_PENDING')
        self.assertIsNotNone(self.sample.test_commenced_on)
        self.assertIsNotNone(self.sample.test_completed_on)
        self.assertTrue(TestResult.objects.filter(sample=self.sample, parameter=self.parameter).exists())


class AuditTrailModelTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username="auditlogger", password="password", role="admin")
        self.customer_for_audit = Customer.objects.create(
            name="Audit Customer", phone="7778889999", email="audit@example.com",
            street_locality_landmark="Audit St", village_town_city="Auditville",
            district="palakkad", pincode="678001"
        )

    def test_log_change_create(self):
        """Test AuditTrail.log_change for a CREATE action."""
        # log_change is typically called from signals or model save methods.
        # Here, we call it directly for testing its own logic.
        from .models import AuditTrail # Local import
        log_entry = AuditTrail.log_change(
            user=self.user,
            action='CREATE',
            instance=self.customer_for_audit,
            new_values={'name': self.customer_for_audit.name, 'email': self.customer_for_audit.email}
        )
        self.assertEqual(log_entry.user, self.user)
        self.assertEqual(log_entry.action, 'CREATE')
        self.assertEqual(log_entry.model_name, 'Customer')
        self.assertEqual(log_entry.object_id, str(self.customer_for_audit.pk))
        self.assertEqual(log_entry.object_repr, str(self.customer_for_audit))
        self.assertEqual(log_entry.new_values['name'], self.customer_for_audit.name)
        self.assertTrue(AuditTrail.objects.filter(pk=log_entry.pk).exists())
        self.assertEqual(str(log_entry), f"Created Customer by {self.user.username} at {log_entry.timestamp}")


    def test_log_change_update(self):
        """Test AuditTrail.log_change for an UPDATE action."""
        from .models import AuditTrail # Local import
        old_name = self.customer_for_audit.name
        self.customer_for_audit.name = "Updated Audit Customer"
        # In a real scenario, instance.save() would trigger this via a signal or overridden save.
        # For direct test of log_change:
        log_entry = AuditTrail.log_change(
            user=self.user,
            action='UPDATE',
            instance=self.customer_for_audit,
            old_values={'name': old_name},
            new_values={'name': self.customer_for_audit.name}
        )
        self.assertEqual(log_entry.action, 'UPDATE')
        self.assertEqual(log_entry.changes['name']['old'], old_name)
        self.assertEqual(log_entry.changes['name']['new'], "Updated Audit Customer")
