from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from .models import Student


class StudentDirectoryTests(TestCase):
    def setUp(self):
        self.student = Student.objects.create(
            student_id='SRCC-TEST-001',
            first_name='Alex',
            last_name='Santos',
            gender='Male',
            date_of_birth='2004-02-15',
            contact_no='09170000001',
        )
        self.staff_user = get_user_model().objects.create_user(
            username='directory_staff',
            password='Test-password-123!',
            is_staff=True,
        )
        self.client.force_login(self.staff_user)

    def test_module_six_pages_remain_available(self):
        for url in ('/', '/Home/', '/registration/', '/registration/success/'):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_legacy_register_url_redirects_to_registration(self):
        response = self.client.get('/Register/')

        self.assertRedirects(response, reverse('student_registration'))

    def test_directory_search_matches_student_id_and_names(self):
        response = self.client.get(reverse('student_list'), {'q': 'sAnToS'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['students']), [self.student])
        self.assertContains(response, self.student.student_id)
        self.assertContains(response, '/static/registration/style.css')

        response = self.client.get(reverse('student_list'), {'q': 'aLeX'})
        self.assertEqual(list(response.context['students']), [self.student])

        response = self.client.get(reverse('student_list'), {'q': 'srcc-test-001'})
        self.assertEqual(list(response.context['students']), [self.student])

    def test_detail_and_update_views_use_the_selected_student(self):
        response = self.client.get(
            reverse('student_detail', args=[self.student.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.student.contact_no)
        self.assertEqual(
            self.client.get(reverse('student_detail', args=[99999])).status_code,
            404,
        )

        response = self.client.post(
            reverse('student_update', args=[self.student.pk]),
            {
                'student_id': self.student.student_id,
                'first_name': 'Alexandra',
                'last_name': 'Santos',
                'gender': 'Female',
                'date_of_birth': '2004-02-15',
                'contact_no': self.student.contact_no,
            },
            follow=True,
        )

        self.assertRedirects(response, reverse('student_detail', args=[self.student.pk]))
        self.assertContains(response, 'Student record updated successfully.')
        self.student.refresh_from_db()
        self.assertEqual(self.student.first_name, 'Alexandra')

    def test_create_form_validates_and_saves_students(self):
        invalid_response = self.client.post(
            reverse('student_create'),
            {'student_id': 'SRCC-TEST-002'},
        )
        self.assertEqual(invalid_response.status_code, 200)
        self.assertFalse(
            Student.objects.filter(student_id='SRCC-TEST-002').exists()
        )

        response = self.client.post(
            reverse('student_create'),
            {
                'student_id': 'SRCC-TEST-002',
                'first_name': 'Jamie',
                'last_name': 'Reyes',
                'gender': 'Female',
                'date_of_birth': '2003-11-08',
                'contact_no': '09170000002',
            },
            follow=True,
        )

        self.assertRedirects(response, reverse('student_list'))
        self.assertContains(response, 'Student record created successfully.')
        self.assertTrue(
            Student.objects.filter(student_id='SRCC-TEST-002').exists()
        )

    def test_delete_requires_post_and_deletes_after_confirmation(self):
        delete_url = reverse('student_delete', args=[self.student.pk])

        response = self.client.get(delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Student.objects.filter(pk=self.student.pk).exists())

        response = self.client.post(delete_url, follow=True)
        self.assertRedirects(response, reverse('student_list'))
        self.assertContains(response, 'Student record deleted successfully.')
        self.assertFalse(Student.objects.filter(pk=self.student.pk).exists())


class AuthenticationTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.staff_user = user_model.objects.create_user(
            username='staff_user',
            password='Test-password-123!',
            is_staff=True,
        )
        self.regular_user = user_model.objects.create_user(
            username='regular_user',
            password='Test-password-123!',
        )
        self.student = Student.objects.create(
            student_id='AUTH-TEST-001',
            first_name='Jordan',
            last_name='Taylor',
            gender='Male',
            date_of_birth='2002-05-10',
            contact_no='09170000003',
        )

    def test_login_page_and_home_login_link_are_available(self):
        response = self.client.get(reverse('login'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Staff Login')
        self.assertContains(response, 'csrfmiddlewaretoken')
        self.assertContains(self.client.get(reverse('home')), reverse('login'))

    def test_valid_staff_login_redirects_to_dashboard(self):
        response = self.client.post(
            reverse('login'),
            {
                'username': 'staff_user',
                'password': 'Test-password-123!',
            },
            follow=True,
        )

        self.assertRedirects(response, reverse('staff_dashboard'))
        self.assertContains(response, 'Welcome, staff_user!')
        self.assertContains(response, reverse('student_list'))

    def test_invalid_login_shows_error(self):
        response = self.client.post(
            reverse('login'),
            {
                'username': 'staff_user',
                'password': 'incorrect-password',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username or password.')

    def test_anonymous_users_are_redirected_from_staff_pages(self):
        protected_urls = (
            reverse('staff_dashboard'),
            reverse('student_list'),
            reverse('student_create'),
            reverse('student_detail', args=[self.student.pk]),
            reverse('student_update', args=[self.student.pk]),
            reverse('student_delete', args=[self.student.pk]),
        )

        for url in protected_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.url.startswith(reverse('login')))

    def test_non_staff_users_cannot_access_staff_pages(self):
        self.client.force_login(self.regular_user)
        protected_urls = (
            reverse('staff_dashboard'),
            reverse('student_list'),
            reverse('student_create'),
            reverse('student_detail', args=[self.student.pk]),
            reverse('student_update', args=[self.student.pk]),
            reverse('student_delete', args=[self.student.pk]),
        )

        for url in protected_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.url.startswith(reverse('login')))

    def test_logout_ends_staff_session(self):
        self.client.force_login(self.staff_user)

        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        response = self.client.post(reverse('logout'), follow=True)

        self.assertRedirects(response, reverse('login'))
        dashboard_response = self.client.get(reverse('staff_dashboard'))
        self.assertEqual(dashboard_response.status_code, 302)
        self.assertTrue(dashboard_response.url.startswith(reverse('login')))

    def test_student_registration_remains_public(self):
        response = self.client.get(reverse('student_registration'))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            reverse('student_registration'),
            {
                'student_id': 'PUBLIC-TEST-001',
                'first_name': 'Casey',
                'last_name': 'Morgan',
                'gender': 'Female',
                'date_of_birth': '2001-08-20',
                'contact_no': '09170000004',
            },
        )

        self.assertRedirects(response, reverse('registration_success'))
        self.assertTrue(
            Student.objects.filter(student_id='PUBLIC-TEST-001').exists()
        )
