from . import profile_blu
from flask import current_app
from flask import g, jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import session

from info import constants
from info import db
from info.models import Category, News
from info.utils.common import user_login_data
from info.utils.image_storage import storage
from info.utils.response_code import RET

@profile_blu.route("/followed_user")
@user_login_data
def user_follow():
    user = g.user

    page =  request.args.get("p",1)

    try:
        page = int(page)
    except Exception as e:
        page = 1

    paginate =  user.followed.paginate(page,4,False)

    items =  paginate.items
    current_page = paginate.page
    total_page = paginate.pages

    users_list = []

    for item in items:
        users_list.append(item.to_dict())

    data = {
        "users":users_list,
        "current_page":current_page,
        "total_page":total_page
    }

    return render_template("news/user_follow.html", data = data)



@profile_blu.route("/info")
@user_login_data
def get_user_info():
    # 当前用户登录
    user = g.user
    if not user:
        return redirect('/')

    data = {
        "user_info":user.to_dict(),
    }

    return render_template("news/user.html",data = data)

@profile_blu.route('/user_info')
@user_login_data
def user_info():
    user = g.user
    if not user:
        return redirect('/')

    data = {
        "user_info": user.to_dict(),
    }

    return render_template("news/user_base_info.html", data=data)

@profile_blu.route('/base_info',methods=['GET','POST'])
@user_login_data
def base_info():
    """
    # 用户基本信息修改
    1.获取用户登录
    2.获取接口参数
    3.更新并保存数据
    4.返回结果

    :return:
    """
    user = g.user
    if request.method == "GET":
        data = {
            "user_info":user.to_dict()
        }
        # 判断当前是否有用户登录
        return render_template('news/user_base_info.html',data = data)

    # 获取接口参数
    data_dict = request.json
    nick_name = data_dict.get('nick_name') #昵称
    gender = data_dict.get('gender') #性别, MAN / WOMEN
    signature = data_dict.get('signature') #签名

    # 判断参数是否为空
    if not all([nick_name,gender,signature]):
        return jsonify(errno=RET.PARAMERR , errmsg='参数有误')

    # 参数的去值范围
    if gender not in (['MAN','WOMAN']):
        return jsonify(errno=RET.PARAMERR ,errmsg='参数错误')

    # 更新保存数据
    user.nick_name = nick_name
    user.gender = gender
    user.signature = signature

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR , errmsg='保存数据失败')

    # session保存数据
    session["nick_name"] = nick_name

    return jsonify(errno=RET.OK, errmsg="更新成功")

@profile_blu.route('/pic_info',methods=["GET","POST"])
@user_login_data
def pic_info():
    user = g.user
    if request.method == "GET":
        data = {
            "user_info":user.to_dict()
        }
        return render_template('news/user_pic_info.html',data = data)

    # 1.获取上传的文件
    try:
        avatar_file = request.files.get("avatar").read()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR , errmsg='读取文件错误')

    #上传七牛云
    try:
        url = storage(avatar_file)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(error=RET.THIRDERR ,errmsg='上传图片错误')

    #将头像信息更新到当前用户
    user.avatar_url = url
    try:
        # 数据保存在数据库
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.OK ,errmsg='ok')

    data = {
        "avatar_url":constants.QINIU_DOMIN_PREFIX + url
    }

    return jsonify(errno=RET.OK , errmsg="OK",data = data)


@profile_blu.route('/pass_info',methods=['GET','POST'])
@user_login_data
def pass_info():
    if request.method == "GET":
        return render_template('news/user_pass_info.html')

    #获取接口参数
    data_dict = request.json
    old_password = data_dict.get("old_password")
    new_password = data_dict.get("new_password")

    if not all([old_password,new_password]):
        return jsonify(errno=RET.PARAMERR,errmsg="参数错误")

    user = g.user
    #获取当前用户登录信息
    if not user.check_password(old_password):
        return jsonify(error=RET.PWDERR,errmsg='原密码错误')

    #更新数据
    user.password = new_password

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg='保存失败')

    return jsonify(errno=RET.OK,errmsg='保存成功')


@profile_blu.route('/collection')
@user_login_data
def user_collection():
    # 个人中心新闻收藏列表
    # 获取页数，默认为1
    p =request.args.get("p",1)
    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        p = 1
    user = g.user
    collections = []
    current_page = 1
    total_page = 1
    try:

        #根据当前用户信息，查询收藏新闻列表，分页数据查询
        paginate = user.collection_news.paginate(p, constants.USER_COLLECTION_MAX_NEWS, False)
        #获取分页数据
        collections = paginate.items
        #获取当前页
        current_page = paginate.page
        #获取总页数
        total_page = paginate.pages
    except Exception as e:
        current_page.logger.error(e)

    collection_dict_li = []
    for news in collections:
        collection_dict_li.append(news.to_dict())

    data = {
        "collections":collections,
        "current_page":current_page,
        "total_page":total_page
    }


    return render_template('news/user_collection.html',data = data)

@profile_blu.route('/news_release',methods =['GET','POST'])
@user_login_data
def news_release():
    # 用户发布新闻
    if request.method == "GET":
        categories = []
        try:
            # 获取所有的分类数据
            categories = Category.query.all()
        except Exception as e:
            current_app.logger.error(e)

        # 定义列表保存分类数据
        categories_dicts = []

        for category in categories:
            # 获取字典
            cate_dict = category.to_dict()
            # 拼接内容
            categories_dicts.append(cate_dict)

        # 移除“最新”分类
        categories_dicts.pop(0)
        data = {
            "categories": categories_dicts
        }
        return render_template('news/user_news_release.html',data = data)

    # POST提交，执行发布新闻操作
    # 1.获取页面数据
    title = request.form.get("title")
    source = '个人发布'
    digest = request.form.get('digest')
    content = request.form.get('content')
    index_image = request.files.get('index_image')
    category_id = request.form.get('category_id')

    # 判断是否有值
    if not all ([title,source,digest,content,index_image,category_id]):
        return jsonify(error=RET.PARAMERR,errmsg='参数有误')

    try:
        # 文件读取，更改为二进制
        index_image = index_image.read()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="图片错误")

    # 将标题图片上传到七牛
    try:
        key = storage(index_image)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg="上传图片错误")

    # 初始化新闻模型数据
    news = News()
    news.title = title
    news.digest = digest
    news.source = source
    news.content = content
    news.index_image_url = constants.QINIU_DOMIN_PREFIX
    news.category_id = category_id
    news.user_id = g.user.id
    # 审核状态
    news.status = 1

    # 保存到数据库，添加新闻内容
    try:
        db.session.add(news)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="保存数据失败")

    return jsonify(errno=RET.OK,errmsg='发布成功,等待审核')


@profile_blu.route('/news_list')
@user_login_data
def news_list():
    # 用户新闻列表

    # 页数
    p = request.args.get("p",1)
    try:
        p=int(p)
    except Exception as e:
        current_app.logger.error(e)
        p=1

    user = g.user
    news_li = []
    current_page = 1
    total_page = 1
    try:
        paginate = News.query.filter(News.user_id == user.id).paginate(p, constants.USER_COLLECTION_MAX_NEWS, False)
        # 分页内容
        news_li = paginate.items
        # 分页页码
        current_page = paginate.page
        # 总页数
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    news_dict_li = []

    for news_item in news_li:
        news_dict_li.append(news_item.to_review_dict())
    data = {
        "news_list" : news_dict_li,
        "total_page" : total_page,
        "current_page" : current_page
    }

    return render_template('news/user_news_list.html',data = data)
