from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import PostForm, CommentForm
from .models import Group, Post, User, Follow
from .utils import paginate_me


def index(request):
    post_list = Post.objects.select_related('group', 'author').all()
    page_obj = paginate_me(post_list, request)
    template = 'posts/index.html'
    context = {
        'page_obj': page_obj,
        'index': True
    }
    return render(request, template, context)


def group_posts(request, any_slug):
    template = 'posts/group_list.html'
    group = get_object_or_404(Group, slug=any_slug)
    post_list = group.posts.select_related('author').all()
    page_obj = paginate_me(post_list, request)
    context = {
        'group': group,
        'page_obj': page_obj,
    }
    return render(request, template, context)


def profile(request, username):
    template = 'posts/profile.html'
    usr = get_object_or_404(User, username=username)
    post_list = usr.posts.select_related('group').all()
    user_posts_count = post_list.count()
    page_obj = paginate_me(post_list, request)
    following = False
    if request.user.is_authenticated:
        following = Follow.objects.filter(
            user=request.user,
            author=usr
        ).exists()
    context = {
        'usr': usr,
        'page_obj': page_obj,
        'user_posts_count': user_posts_count,
        'following': following
    }
    return render(request, template, context)


def post_detail(request, post_id):
    template = 'posts/post_detail.html'
    post = get_object_or_404(Post, id=post_id)
    user_posts_count = post.author.posts.all().count()
    form = CommentForm(request.POST or None)
    comments = post.comments.select_related('author').all()
    context = {
        'post': post,
        'user_posts_count': user_posts_count,
        'form': form,
        'comments': comments
    }
    return render(request, template, context)


@login_required
def post_create(request):
    template = 'posts/create_post.html'
    form = PostForm(request.POST or None, files=request.FILES or None)
    if form.is_valid():
        new_post = form.save(commit=False)
        new_post.author = request.user
        new_post.save()
        return redirect(
            reverse(
                'posts:profile',
                kwargs={'username': request.user.username}))
    context = {
        'form': form,
    }
    return render(request, template, context)


@login_required
def post_edit(request, post_id):
    template = 'posts/create_post.html'
    post = get_object_or_404(Post, id=post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if request.user != post.author:
        return redirect(
            reverse(
                'posts:post_detail',
                kwargs={'post_id': post_id}))
    elif form.is_valid():
        form.save()
        return redirect(
            reverse(
                'posts:post_detail',
                kwargs={'post_id': post_id}))
    else:
        context = {
            'form': form,
            'is_edit': 'true',
            'post_id': post_id
        }
        return render(request, template, context)


@login_required
def add_comment(request, post_id):
    form = CommentForm(request.POST or None)
    post = get_object_or_404(Post, id=post_id)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    usr = get_object_or_404(User, username=request.user)
    follow_list = Follow.objects.filter(user=usr).values('author')
    post_list = Post.objects.filter(author__in=follow_list).select_related(
        'group',
        'author'
    )
    page_obj = paginate_me(post_list, request)
    template = 'posts/follow.html'
    context = {
        'page_obj': page_obj,
        'follow': True
    }
    return render(request, template, context)


@login_required
def profile_follow(request, username):
    following = get_object_or_404(User, username=username)
    if following != request.user:
        Follow.objects.get_or_create(
            user=request.user,
            author=following
        )
    return redirect(
        reverse(
            'posts:profile',
            kwargs={'username': username}))


@login_required
def profile_unfollow(request, username):
    following = get_object_or_404(User, username=username)
    Follow.objects.filter(
        user=request.user,
        author=following
    ).delete()
    return redirect(
        reverse(
            'posts:profile',
            kwargs={'username': username}))
