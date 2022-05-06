import shutil
import tempfile
import math

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Group, Post, Follow

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.user = User.objects.create_user(username='HasNoName')
        cls.another_user = User.objects.create_user(username='HasNoName2')
        cls.following_user = User.objects.create_user(username='Following')
        cls.grp = Group.objects.create(
            title='Название тестовой группы',
            slug='test1',
            description='Описание тестовой группы'
        )
        cls.another_grp = Group.objects.create(
            title='Название тестовой группы 2',
            slug='test2',
            description='Описание тестовой группы'
        )
        cls.all_post_ids = []
        cls.images_names = {}
        cls.grp_post_ids = []
        for i in range(1, settings.PAGE_ROWS_COUNT + 3):
            cls.uploaded = SimpleUploadedFile(
                name=f'small_{str(i)}.gif',
                content=cls.small_gif,
                content_type='image/gif'
            )
            cls.user_post = Post.objects.create(
                text='Текст тестового поста',
                author=cls.user,
                group=cls.grp,
                image=cls.uploaded
            )
            cls.images_names[str(cls.user_post.pk)] = f'small_{str(i)}.gif'
            cls.grp_post_ids.append(cls.user_post.pk)
        cls.post = Post.objects.create(
            text='Текст тестового поста с другой группой',
            author=cls.another_user,
            group=cls.another_grp
        )
        cls.all_post_ids = cls.grp_post_ids
        cls.all_post_ids.append(cls.post.pk)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.another_auth_client = Client()
        self.another_auth_client.force_login(self.another_user)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_pages_uses_correct_template(self):
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={
                'any_slug': self.grp.slug
            }): 'posts/group_list.html',
            reverse('posts:profile', kwargs={
                'username': self.user.username
            }): 'posts/profile.html',
            reverse('posts:post_detail', kwargs={
                'post_id': self.user_post.pk
            }): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit', kwargs={
                'post_id': self.user_post.pk
            }): 'posts/create_post.html'
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def post_test(self, obj, type=None):
        """ Проверка поста """
        if type == 'all posts':
            self.assertIn(obj.pk, self.all_post_ids)
        else:
            self.assertIn(obj.pk, self.grp_post_ids)
        if obj.group == self.another_grp:
            self.assertEqual(obj.text, self.post.text)
            self.assertEqual(obj.author, self.post.author)
            self.assertEqual(obj.group, self.post.group)
            self.assertEqual(obj.image, self.images_names[str(obj.pk)])
        else:
            self.assertEqual(obj.text, self.user_post.text)
            self.assertEqual(obj.author, self.user_post.author)
            self.assertEqual(obj.group, self.user_post.group)

    def postlist_testing(self, address, type=None):
        """ Проверка списка постов и паджинатора """
        response = self.authorized_client.get(address)
        if type == 'all posts':
            for obj in response.context['page_obj']:
                self.post_test(obj, type)
                post_cnt = Post.objects.count()
        elif type == 'another grp':
            post_cnt = self.another_grp.posts.count()
        elif type == 'grp':
            post_cnt = self.grp.posts.count()
        elif type == 'user':
            post_cnt = self.user.posts.count()
        if 0 < post_cnt <= settings.PAGE_ROWS_COUNT:
            self.assertEqual(
                len(response.context['page_obj']),
                post_cnt
            )
        elif post_cnt >= settings.PAGE_ROWS_COUNT:
            self.assertEqual(
                len(response.context['page_obj']),
                settings.PAGE_ROWS_COUNT
            )
        response = self.authorized_client.get(
            address + '?page=2'
        )
        if settings.PAGE_ROWS_COUNT < post_cnt <= settings.PAGE_ROWS_COUNT * 2:
            self.assertEqual(
                len(response.context['page_obj']),
                post_cnt - settings.PAGE_ROWS_COUNT
            )
        elif post_cnt > settings.PAGE_ROWS_COUNT * 2:
            self.assertEqual(
                len(response.context['page_obj']),
                settings.PAGE_ROWS_COUNT
            )

    def test_index_page_show_correct_context(self):
        self.postlist_testing(reverse('posts:index'), 'all posts')

    def test_grp_list_page_show_correct_context(self):
        address = reverse('posts:group_list', kwargs={
            'any_slug': self.grp.slug
        })
        self.postlist_testing(address, 'grp')

    def test_another_grp_page_correct_context(self):
        address = reverse('posts:group_list', kwargs={
            'any_slug': self.another_grp.slug
        })
        self.postlist_testing(address, 'another grp')

    def test_profile_page_show_correct_context(self):
        address = reverse('posts:profile', kwargs={
            'username': self.user.username
        })
        self.postlist_testing(address, 'user')

    def test_post_det_page_show_correct_context(self):
        response = self.client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.user_post.pk})
        )
        post = response.context['post']
        self.post_test(post)
        post_count = self.user_post.author.posts.count()
        self.assertEqual(response.context['user_posts_count'], post_count)

    def test_post_cred_page_show_correct_context(self):
        response = {
            'edit': self.authorized_client.get(reverse(
                'posts:post_edit', kwargs={'post_id': self.user_post.pk})
            ),
            'create': self.authorized_client.get(reverse('posts:post_create'))
        }
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                for resp in response:
                    form_field = response[resp].context.get(
                        'form'
                    ).fields.get(value)
                    self.assertIsInstance(form_field, expected)
        self.assertEqual(
            response['edit'].context['post_id'],
            self.user_post.pk
        )
        self.assertEqual(response['edit'].context['is_edit'], 'true')

    def test_cache_index_page_contex(self):
        new_post = Post.objects.create(
            text='Текст тестового поста для тестирования кэша',
            author=self.user,
            group=self.grp
        )
        post_count = self.user_post.author.posts.count()
        pages = math.ceil(post_count / settings.PAGE_ROWS_COUNT)
        cache.clear()
        response = self.client.get(
            reverse('posts:index') + f'?page={str(pages)}'
        )
        self.assertIn(new_post, response.context['page_obj'])
        key = make_template_fragment_key('index_page', str(pages))
        cache1 = cache.get(key)  # сохранили кэш (1)
        new_post.delete()  # удалили пост
        cache2 = cache.get(key)  # сохранили кэш (2)
        self.assertEqual(cache1, cache2)  # кэши одинаковые
        cache.clear()  # очистили кэш
        cache3 = cache.get(key)  # сохранили кэш (3)
        self.assertNotEqual(cache1, cache3)  # кэши разные

    def test_anon_profile_follow(self):
        follow_count = Follow.objects.count()
        self.client.get(
            reverse('posts:profile_follow', kwargs={
                'username': self.another_user.username
            })
        )
        self.assertEqual(Follow.objects.count(), follow_count)

    def test_auth_profile_follow(self):
        Follow.objects.filter(user=self.user).delete()
        follow_count = Follow.objects.count()
        self.authorized_client.get(
            reverse('posts:profile_follow', kwargs={
                'username': self.another_user.username
            })
        )
        self.assertEqual(Follow.objects.count(), follow_count + 1)
        self.assertTrue(
            Follow.objects.filter(
                user=self.user,
                author=self.another_user
            ).exists()
        )

    def test_auth_profile_unfollow(self):
        Follow.objects.get_or_create(
            user=self.user,
            author=self.another_user
        )
        follow_count = Follow.objects.count()
        self.authorized_client.get(
            reverse('posts:profile_unfollow', kwargs={
                'username': self.another_user.username
            })
        )
        self.assertEqual(Follow.objects.count(), follow_count - 1)
        self.assertFalse(
            Follow.objects.filter(
                user=self.user,
                author=self.another_user
            ).exists()
        )

    def test_index_follow(self):
        Post.objects.filter(
            author=self.following_user,
        ).delete()
        new_post = Post.objects.create(
            text='Текст тестового поста от following_user',
            author=self.following_user,
            group=self.grp
        )
        Follow.objects.filter(
            user=self.user
        ).delete()
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertNotIn(new_post, response.context['page_obj'])
        Follow.objects.create(
            user=self.user,
            author=self.following_user
        )
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertIn(new_post, response.context['page_obj'])
