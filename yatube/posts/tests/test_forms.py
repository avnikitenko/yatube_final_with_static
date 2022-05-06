import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Post, User, Group, Comment

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
def upload_image(cnt):
    small_gif = (
        b'\x47\x49\x46\x38\x39\x61\x02\x00'
        b'\x01\x00\x80\x00\x00\x00\x00\x00'
        b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
        b'\x00\x00\x00\x2C\x00\x00\x00\x00'
        b'\x02\x00\x01\x00\x00\x02\x02\x0C'
        b'\x0A\x00\x3B'
    )
    return SimpleUploadedFile(
        name=f'small_image_{str(cnt)}.gif',
        content=small_gif,
        content_type='image/gif'
    )


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsFormsTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='HasNoName')
        cls.group = Group.objects.create(
            title='Тестовая группа (1)',
            slug='test1',
            description='Описание тестовой группы (1)',
        )
        cls.another_group = Group.objects.create(
            title='Тестовая группа (2)',
            slug='test2',
            description='Описание тестовой группы (2)',
        )
        post_image = upload_image(1)
        cls.post = Post.objects.create(
            text='Текст тестового поста',
            author=cls.user,
            group=cls.group,
            image=post_image
        )
        anon_create_image = upload_image(2)
        create_image = upload_image(3)
        anon_edit_image = upload_image(4)
        edit_image = upload_image(5)
        cls.form_data = {
            'anon_create': {
                'text': 'Текст тестового поста (2)',
                'group': cls.group.pk,
                'image': anon_create_image
            },
            'create': {
                'text': 'Текст тестового поста (2)',
                'group': cls.group.pk,
                'image': create_image
            },
            'anon_edit': {
                'text': 'Измененный текст поста',
                'group': cls.another_group.pk,
                'image': anon_edit_image
            },
            'edit': {
                'text': 'Измененный текст поста',
                'group': cls.another_group.pk,
                'image': edit_image
            }
        }
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.user,
            text='Текст нового комментария'
        )
        cls.comment_form_data = {
            'text': 'Текст (2) нового комментария'
        }

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_post_create_anon_form(self):
        address = reverse('posts:post_create')
        post_count = Post.objects.count()
        create_form_data = self.form_data['anon_create']
        response = self.client.post(
            address,
            data=create_form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), post_count)
        self.assertRedirects(
            response,
            reverse('users:login') + '?next=' + address
        )

    def test_post_create_auth_form(self):
        address = reverse('posts:post_create')
        post_count = Post.objects.count()
        create_form_data = self.form_data['create']
        response = self.authorized_client.post(
            address,
            data=create_form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertRedirects(response, reverse('posts:profile', kwargs={
            'username': self.user.username
        }))
        last_post = Post.objects.all().order_by('-id').first()
        self.assertEqual(last_post.text, create_form_data['text'])
        self.assertEqual(last_post.group.pk, create_form_data['group'])
        self.assertEqual(last_post.author, self.user)
        self.assertEqual(
            last_post.image.name.split('/')[-1],
            create_form_data['image'].name
        )

    def test_post_edit_anon_form(self):
        address = reverse('posts:post_edit', kwargs={'post_id': self.post.pk})
        post_count = Post.objects.count()
        edit_form_data = self.form_data['anon_edit']
        response_anon = self.client.post(
            address,
            data=edit_form_data,
            follow=True
        )
        self.post.refresh_from_db()
        self.assertTrue(  # вернет True, если ничего не изменилось
            Post.objects.filter(
                id=self.post.pk,
                text=self.post.text,
                group=self.post.group,
                author=self.user.pk,
                image=self.post.image
            ).exists()
        )
        self.assertEqual(Post.objects.count(), post_count)
        self.assertRedirects(
            response_anon,
            reverse('users:login') + '?next=' + address
        )

    def test_post_edit_auth_form(self):
        address = reverse('posts:post_edit', kwargs={'post_id': self.post.pk})
        post_count = Post.objects.count()
        edit_form_data = self.form_data['edit']
        response = self.authorized_client.post(
            address,
            data=edit_form_data,
            follow=True
        )
        self.assertRedirects(response, reverse('posts:post_detail', kwargs={
            'post_id': self.post.pk
        }))
        self.post.refresh_from_db()
        self.assertEqual(Post.objects.count(), post_count)
        post = Post.objects.filter(id=self.post.pk).first()
        self.assertEqual(post.text, edit_form_data['text'])
        self.assertEqual(post.group.pk, edit_form_data['group'])
        self.assertEqual(post.author, self.user)
        self.assertEqual(
            post.image.name.split('/')[-1],
            edit_form_data['image'].name
        )

    def test_comment_create_anon_form(self):
        address = reverse('posts:add_comment', kwargs={
            'post_id': self.post.pk
        })
        comment_count = Comment.objects.count()
        response = self.client.post(
            address,
            data=self.comment_form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comment_count)
        self.assertRedirects(
            response,
            reverse('users:login') + '?next=' + address
        )

    def test_comment_create_auth_form(self):
        address = reverse('posts:add_comment', kwargs={
            'post_id': self.post.pk
        })
        comment_count = Comment.objects.count()
        response = self.authorized_client.post(
            address,
            data=self.comment_form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comment_count + 1)
        self.assertRedirects(response, reverse('posts:post_detail', kwargs={
            'post_id': self.comment.post.pk
        }))
        last_comment = Comment.objects.all().order_by('-id').first()
        self.assertEqual(last_comment.text, self.comment_form_data['text'])
        resp_redir = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={
                'post_id': self.comment.post.pk
            })
        )
        self.assertIn(self.comment, resp_redir.context['comments'])
