from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from posts.models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='HasNoName')
        cls.another_user = User.objects.create_user(username='AnothHasNoName')
        cls.grp = Group.objects.create(
            title='Название тестовой группы',
            slug='test1',
            description='Описание тестовой группы'
        )
        cls.post = Post.objects.create(
            text='Текст тестового поста',
            author=cls.user,
            group=cls.grp
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.another_authorized_client = Client()
        self.another_authorized_client.force_login(self.another_user)
        self.all_urls = {  # словарь с общей информацией для тестов URLов
            'posts-index': {
                'url': '/',
                'template': 'posts/index.html',
                'resp': [
                    {
                        'client': self.client,
                        'HTTPstatus': HTTPStatus(200),
                    }
                ]
            },
            'posts-profile': {
                'url': '/profile/' + self.user.username + '/',
                'template': 'posts/profile.html',
                'resp': [
                    {
                        'client': self.client,
                        'HTTPstatus': HTTPStatus(200),
                    }
                ]
            },
            'posts-group': {
                'url': '/group/' + self.grp.slug + '/',
                'template': 'posts/group_list.html',
                'resp': [
                    {
                        'client': self.client,
                        'HTTPstatus': HTTPStatus(200),
                    }
                ]
            },
            'posts-detail': {
                'url': '/posts/' + str(self.post.pk) + '/',
                'template': 'posts/post_detail.html',
                'resp': [
                    {
                        'client': self.client,
                        'HTTPstatus': HTTPStatus(200),
                    }
                ]
            },
            'posts-create': {
                'url': '/create/',
                'template': 'posts/create_post.html',
                'resp': [
                    {
                        'client': self.client,
                        'HTTPstatus': HTTPStatus(302),
                    },
                    {
                        'client': self.authorized_client,
                        'HTTPstatus': HTTPStatus(200)
                    },
                ]
            },
            'post-edit': {
                'url': '/posts/' + str(self.post.pk) + '/edit/',
                'template': 'posts/create_post.html',
                'resp': [
                    {
                        'client': self.client,
                        'HTTPstatus': HTTPStatus(302),
                    },
                    {
                        'client': self.another_authorized_client,
                        'HTTPstatus': HTTPStatus(302),
                    },
                    {
                        'client': self.authorized_client,
                        'HTTPstatus': HTTPStatus(200)
                    },
                ]
            },
            'not-exists': {
                'url': '/NotExists/',
                'template': 'core/404.html',
                'resp': [
                    {
                        'client': self.client,
                        'HTTPstatus': HTTPStatus(404),
                    },
                    {
                        'client': self.authorized_client,
                        'HTTPstatus': HTTPStatus(404)
                    },
                ]
            },
            'about-tech': {
                'url': '/about/tech/',
                'resp': [
                    {
                        'client': self.client,
                        'HTTPstatus': HTTPStatus(200)
                    }
                ]
            },
            'about-author': {
                'url': '/about/author/',
                'resp': [
                    {
                        'client': self.client,
                        'HTTPstatus': HTTPStatus(200)
                    },
                ]
            }
        }

    def test_urls_pages(self):
        for page in self.all_urls:
            test_page = self.all_urls[page]
            if 'template' in test_page.keys():
                response = self.authorized_client.get(test_page['url'])
                self.assertTemplateUsed(response, test_page['template'])
            responses = test_page['resp']
            for resp in responses:
                response = resp['client'].get(test_page['url'])
                self.assertEqual(response.status_code, resp['HTTPstatus'])
