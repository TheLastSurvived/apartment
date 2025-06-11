from flask import Flask, render_template, request, flash, redirect, session, url_for, abort, jsonify, json
from flask_sqlalchemy import SQLAlchemy
from flask_ckeditor import CKEditor
from datetime import datetime, timedelta
import uuid
from werkzeug.utils import secure_filename
from hashlib import md5
from  sqlalchemy.sql.expression import func
from flask_admin import AdminIndexView, expose
from flask_admin.contrib.sqlamodel import ModelView
from flask_admin import Admin
from flask_migrate import Migrate
from sqlalchemy import or_,case,and_  
import os
from markupsafe import Markup
from flask_admin.form import ImageUploadField
import re

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'
app.config['UPLOAD_FOLDER'] = 'static/img/upload'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
db = SQLAlchemy(app)
ckeditor = CKEditor(app)
migrate = Migrate(app, db)


def convert_links(text):
    # Регулярное выражение для поиска ссылок в формате [текст](URL)
    link_pattern = re.compile(r'\[(.*?)\]\((.*?)\)')
    # Заменяем все вхождения на HTML-ссылки
    return Markup(link_pattern.sub(r'<a href="\2" class="notification-link" target="_blank">\1</a>', text))

# Добавляем фильтр в Jinja2
app.jinja_env.filters['convert_links'] = convert_links


class Users(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(100))
    surname = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100), unique=True)
    root = db.Column(db.Integer, default=0)
    avatar = db.Column(db.String(120), default='default.jpg')
    
    articles = db.relationship('Articles', backref='users', lazy=True)
       
    def __repr__(self):
        return 'User %r' % self.id 
    
    
class Articles(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    title = db.Column(db.String(100))
    text = db.Column(db.Text)
    image_name = db.Column(db.String(100))
    category = db.Column(db.String(100))
    price = db.Column(db.Integer)
    floor = db.Column(db.Integer)
    entrance = db.Column(db.Integer)
    type_app = db.Column(db.String(100))
    address= db.Column(db.String(100))
    count_rooms = db.Column(db.Integer)
    hide = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    id_user = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    orders = db.relationship('Orders', backref='article', lazy=True)
    images = db.relationship('Image', backref='article', lazy=True, cascade="all, delete-orphan")

   
    def __repr__(self):
        return 'Articles %r' % self.id 
    

class Orders(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    id_user = db.Column(db.Integer, db.ForeignKey('users.id'))
    id_article = db.Column(db.Integer, db.ForeignKey('articles.id'))
    date = db.Column(db.DateTime)

    def __repr__(self):
        return 'Orders %r' % self.id 


class Messages(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    
    sender = db.relationship('Users', foreign_keys=[sender_id])
    recipient = db.relationship('Users', foreign_keys=[recipient_id])
    article = db.relationship('Articles')  
      
    def __repr__(self):
        return f'<Message {self.id}>'
    

class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))
    image_name = db.Column(db.String(255))


    def __repr__(self):
        return f'<Image {self.id}>'
  
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))
    redirect_to_chat = db.Column(db.Boolean, default=False)  # Флаг для перенаправления в чат
    chat_article_id = db.Column(db.Integer)  # ID статьи для чата
    chat_user_id = db.Column(db.Integer)  # ID пользователя для чата
    
    user = db.relationship('Users', backref='notifications')
    article = db.relationship('Articles')  

class AdminIndex(AdminIndexView):
    @expose('/', methods=['GET', 'POST'])
    def index(self):
        if 'name' in session:
            user = Users.query.filter_by(email=session['name']).first()
            if user.root!=1:
                abort(403)
            else:
                return self.render('admin/dashboard_index.html')
        else:
            abort(401)


admin = Admin(app, name='Аренда365')


class OrdersView(ModelView):
    column_display_pk = True 
    column_hide_backrefs = False
    column_list = ['id', 'id_user','id_article', 'date']
    
    
class ArticlesView(ModelView):
    column_display_pk = True 
    column_hide_backrefs = False
    column_list = ['id', 'title','text', 'image_name','category','price','type_app','address', 'entrance','floor','hide','id_user', 'created_at']

    form_widget_args = {
        'image_name': {
            'readonly': True
        }
    }

    form_extra_fields = {
        'image_preview': ImageUploadField('Image', base_path='static/img/upload')
    }
    
    def _image_preview_formatter(view, context, model, name):
        return Markup(f'<img src="../../static/img/upload/{model.image_name}" width="200">')

    column_formatters = {
        'image_name': _image_preview_formatter
    }

    

class MessagesView(ModelView):
    column_display_pk = True 
    column_hide_backrefs = False
    column_list = ['id', 'content','timestamp', 'sender_id','recipient_id','article_id','is_read']


class ImageView(ModelView):
    column_display_pk = True 
    column_hide_backrefs = False
    column_list = ['id', 'article_id','image_name']


admin.add_view(ModelView(Users, db.session))
admin.add_view(ArticlesView(Articles, db.session))
admin.add_view(OrdersView(Orders, db.session))
admin.add_view(MessagesView(Messages, db.session))
admin.add_view(ImageView(Image, db.session))
admin.add_view(ModelView(Notification, db.session))

@app.route('/', methods=['GET', 'POST'])
def index():
    random_articles = Articles.query.order_by(func.random()).limit(3).all()
    return render_template("index.html",random_articles=random_articles)


@app.route('/moderation-articles')
def moderation_articles():
    if not 'name' in session:
        abort(401)
    
    current_user = Users.query.filter_by(email=session['name']).first()
    articles = Articles.query.filter_by(id_user=current_user.id, hide=True).all()
    
    return render_template("moderation_articles.html", articles=articles)


@app.route('/chat/<int:article_id>/<int:recipient_id>')
def chat(article_id, recipient_id):
    current_user = Users.query.filter_by(email=session['name']).first()
    article = Articles.query.get_or_404(article_id)
    recipient = Users.query.get_or_404(recipient_id)
    # Определяем, кто является арендодателем (владелец объявления)
    landlord_id = article.id_user
    
    # Определяем, кто является арендатором
    # Если текущий пользователь - владелец объявления, то recipient_id - арендатор
    # Иначе текущий пользователь - арендатор, а recipient_id должен быть владельцем
    if current_user.id == landlord_id:
        tenant_id = recipient_id
        # Проверяем, что переданный recipient_id действительно арендовал это жилье
        if not Orders.query.filter_by(id_article=article_id, id_user=recipient_id).first():
            abort(403, description="Этот пользователь не арендовал данное жилье")
    else:
        tenant_id = current_user.id
        # Проверяем, что текущий пользователь арендовал это жилье
        if not Orders.query.filter_by(id_article=article_id, id_user=current_user.id).first():
            abort(403, description="Вы не арендовали данное жилье")
        # Убеждаемся, что recipient_id - это владелец объявления
        if recipient_id != landlord_id:
            abort(403, description="Некорректный собеседник")
    
    # Получаем данные собеседника
    interlocutor = Users.query.get_or_404(recipient_id)
    
    # Получаем сообщения
    messages = Messages.query.filter(
        ((Messages.sender_id == current_user.id) & (Messages.recipient_id == recipient_id)) |
        ((Messages.sender_id == recipient_id) & (Messages.recipient_id == current_user.id)),
        Messages.article_id == article_id
    ).order_by(Messages.timestamp.asc()).all()
    
    # Помечаем сообщения как прочитанные
    for message in messages:
        if message.recipient_id == current_user.id and not message.is_read:
            message.is_read = True
            db.session.commit()
    
    return render_template('chat.html', 
                         messages=messages, 
                         article=article, 
                         interlocutor=interlocutor,
                         current_user=current_user,
                         is_landlord=current_user.id == landlord_id,recipient=recipient)


@app.route('/send_message/<int:article_id>/<int:recipient_id>', methods=['POST'])
def send_message(article_id, recipient_id):
    current_user = Users.query.filter_by(email=session['name']).first()
    content = request.form.get('content')
    if content:
        new_message = Messages(
            content=content,
            sender_id=current_user.id,
            recipient_id=recipient_id,
            article_id=article_id
        )
        db.session.add(new_message)
        db.session.commit()
    return redirect(url_for('chat', article_id=article_id, recipient_id=recipient_id))


@app.route('/my_chats')
def my_chats():
    current_user = Users.query.filter_by(email=session['name']).first()
    
    # Получаем уникальные комбинации article_id + собеседник
    chat_combinations = db.session.query(
        Messages.article_id,
        case(
            (Messages.sender_id == current_user.id, Messages.recipient_id),
            else_=Messages.sender_id
        ).label('interlocutor_id')
    ).filter(
        or_(
            Messages.sender_id == current_user.id,
            Messages.recipient_id == current_user.id
        )
    ).distinct().all()
    
    # Собираем данные для каждого чата
    chats = []
    for combo in chat_combinations:
        article = Articles.query.get(combo.article_id)
        interlocutor = Users.query.get(combo.interlocutor_id)
        
        # Получаем количество непрочитанных сообщений
        unread_count = Messages.query.filter(
            Messages.article_id == combo.article_id,
            Messages.sender_id == combo.interlocutor_id,
            Messages.recipient_id == current_user.id,
            Messages.is_read == False
        ).count()
        
        # Получаем последнее сообщение (для preview)
        last_message = Messages.query.filter(
            or_(
                and_(
                    Messages.sender_id == current_user.id,
                    Messages.recipient_id == combo.interlocutor_id,
                    Messages.article_id == combo.article_id
                ),
                and_(
                    Messages.sender_id == combo.interlocutor_id,
                    Messages.recipient_id == current_user.id,
                    Messages.article_id == combo.article_id
                )
            )
        ).order_by(Messages.timestamp.desc()).first()
        
        chats.append({
            'article_id': combo.article_id,
            'article_title': article.title,
            'interlocutor_id': combo.interlocutor_id,
            'interlocutor_name': f"{interlocutor.name} {interlocutor.surname}",
            'unread_count': unread_count,
            'last_message_preview': last_message.content[:50] + "..." if last_message else "",
            'last_message_time': last_message.timestamp if last_message else None
        })
    
    # Сортируем по времени последнего сообщения
    chats.sort(key=lambda x: x['last_message_time'] or datetime.min, reverse=True)
    
    return render_template('my_chats.html', chats=chats)


@app.route('/update-article-galery/<int:id>', methods=['POST'])
def update_article(id):
    if 'images' in request.files:
        files = request.files.getlist('images')
        
        # Проверяем количество файлов
        if len(files) > 5:
            flash("Максимум 5 изображения!", "bad")
            return redirect(url_for('card', id=id))
        
        # Проверяем общее количество изображений у статьи
        existing_images = Image.query.filter_by(article_id=id).count()
        if existing_images + len(files) > 5:
            flash(f"В записе уже {existing_images} изображений. В данный момент дожно добавить только {5 - existing_images}.", "bad")
            return redirect(url_for('card', id=id))

        # Сохраняем файлы
        for file in files:
            if file.filename != '':
                if not allowed_file(file.filename):
                    flash("Недопустимый формат файла!", "bad")
                    continue
                
                filename = secure_filename(file.filename)
                unique_filename = str(uuid.uuid4()) + "_" + filename
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)
                
                new_image = Image(article_id=id, image_name=unique_filename)
                db.session.add(new_image)
        
        db.session.commit()
        flash("Изображения успешно загружены!", "ok")
    
    return redirect(url_for('card', id=id))


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/delete-image/<int:image_id>')
def delete_image(image_id):
    image = Image.query.get_or_404(image_id)
    current_user = Users.query.filter_by(email=session['name']).first()
    
    # Проверяем, что пользователь имеет права на удаление
    if image.article.id_user != current_user.id and current_user.root != 1:
        abort(403)
    
    try:
        # Удаляем файл с диска
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], image.image_name)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Удаляем запись из БД
        db.session.delete(image)
        db.session.commit()
        flash("Изображение удалено!", "ok")
    except Exception as e:
        db.session.rollback()
        flash("Ошибка при удалении изображения!", "bad")
        app.logger.error(f"Error deleting image: {str(e)}")
    
    return redirect(url_for('card', id=image.article_id))


@app.context_processor
def inject_unread_messages():
    if 'name' in session:
        current_user = Users.query.filter_by(email=session['name']).first()

        unread_count = Messages.query.filter_by(recipient_id=current_user.id, is_read=False).count()
        return dict(unread_messages=unread_count)
    return dict(unread_messages=0)


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if not 'name' in session:
        abort(401)
    total_user = Users.query.filter_by(email=session['name']).first()
    articles = Articles.query.filter_by(id_user=total_user.id).all()
    orders = Orders.query.filter_by(id_user=total_user.id).join(Articles).all()
    notifications = Notification.query.filter_by(user_id=total_user.id)\
        .order_by(Notification.created_at.desc()).all()
    if request.method == 'POST':
        title = request.form.get('name')
        address = request.form.get('address')
        category = request.form.get('category')
        type_app = request.form.get('type')
        price = request.form.get('price')
        count_rooms = request.form.get('count_rooms')
        floor = request.form.get('floor')
        entrance = request.form.get('entrance')
        image = request.files['image']
        filename = secure_filename(image.filename)
        pic_name = str(uuid.uuid4()) + "_" + filename
        image.save("static/img/upload/" + pic_name)
        text = request.form.get('ckeditor')
        article = Articles(entrance=entrance,floor=floor,title=title,address=address,category=category,type_app=type_app,price=price,image_name=pic_name,text=text,id_user=total_user.id,count_rooms=count_rooms)
        db.session.add(article)
        db.session.commit()
        notification = Notification(
            user_id=total_user.id,
            message=f"Ваше объявление '{article.title}' создано и ожидает модерации",
            article_id=article.id,
            is_read=False
        )
        db.session.add(notification)
        db.session.commit()
        flash("Запись добавлена!", category="ok")
        return redirect(url_for("profile"))
    return render_template("profile.html",articles=articles,orders=orders,notifications=notifications)


@app.route('/mark-notification-as-read/<int:notification_id>')
def mark_notification_as_read(notification_id):
    if not 'name' in session:
        abort(401)
    
    notification = Notification.query.get_or_404(notification_id)
    user = Users.query.filter_by(email=session['name']).first()
    
    if notification.user_id != user.id:
        abort(403)
    
    notification.is_read = True
    db.session.commit()
    current_user = Users.query.filter_by(email=session['name']).first()
    if notification.redirect_to_chat:
        # Для владельца объявления: чат с арендатором (chat_user_id)
        # Для арендатора: чат с владельцем (user_id объявления)
        if notification.user_id == current_user.id:
            # Это владелец объявления - открываем чат с арендатором
            return redirect(url_for('chat', 
                                 article_id=notification.chat_article_id, 
                                 recipient_id=notification.chat_user_id))
        else:
            # Это арендатор - открываем чат с владельцем
            article = Articles.query.get(notification.chat_article_id)
            return redirect(url_for('chat',
                                 article_id=notification.chat_article_id,
                                 recipient_id=article.id_user))
    
    return redirect(url_for('profile'))


@app.route('/mark-all-notifications-as-read', methods=['GET'])
def mark_all_as_read():
    if not 'name' in session:
        abort(401)
    
    user = Users.query.filter_by(email=session['name']).first()
    Notification.query.filter_by(user_id=user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    
    return redirect(url_for('profile'))


@app.route('/catalog')
def catalog():
    if request.method == 'GET':
        category = request.args.get('category')
        min_price = request.args.get('min_price')
        max_price = request.args.get('max_price')
        type_app = request.args.get('type_app')
        region = request.args.get('region')
        city = request.args.get('city')
        available_date_str = request.args.get('available_date')
        available_date = datetime.strptime(available_date_str, "%Y-%m-%d") if available_date_str else None
        count_rooms = request.args.get('room_type')
        
        min_price_all = db.session.query(func.min(Articles.price)).scalar()
        max_price_all = db.session.query(func.max(Articles.price)).scalar()
        query = Articles.query
        
        # Словарь городов по областям (должен соответствовать тому, что в шаблоне)
        cities_by_region = {
            'Брестская область': ['Брест', 'Барановичи', 'Пинск', 'Кобрин', 'Берёза', 'Лунинец', 'Ивацевичи', 'Пружаны', 'Иваново', 'Дрогичин', 'Ганцевичи', 'Жабинка', 'Столин', 'Микашевичи', 'Белоозёрск', 'Малорита', 'Ляховичи', 'Каменец'],
            'Витебская область': ['Витебск', 'Орша', 'Новополоцк', 'Полоцк', 'Поставы', 'Глубокое', 'Лепель', 'Новолукомль', 'Городок', 'Барань', 'Толочин', 'Браслав', 'Чашники', 'Миоры', 'Дубровно', 'Докшицы', 'Верхнедвинск', 'Сенно'],
            'Гомельская область': ['Гомель', 'Мозырь', 'Жлобин', 'Светлогорск', 'Речица', 'Калинковичи', 'Рогачёв', 'Добруш', 'Житковичи', 'Хойники', 'Петриков', 'Ельск', 'Буда-Кошелёво', 'Наровля', 'Ветка', 'Чечерск', 'Октябрьский', 'Лельчицы'],
            'Гродненская область': ['Гродно', 'Лида', 'Слоним', 'Волковыск', 'Сморгонь', 'Новогрудок', 'Ошмяны', 'Щучин', 'Мосты', 'Берёзовка', 'Ивье', 'Дятлово', 'Скидель', 'Островец', 'Кореличи', 'Вороново', 'Зельва', 'Свислочь'],
            'Минская область': ['Минск', 'Борисов', 'Солигорск', 'Молодечно', 'Жодино', 'Слуцк', 'Вилейка', 'Дзержинск', 'Марьина Горка', 'Столбцы', 'Несвиж', 'Заславль', 'Фаниполь', 'Березино', 'Любань', 'Старые Дороги', 'Воложин', 'Узда', 'Копыль', 'Клецк', 'Червень', 'Смолевичи', 'Мядель'],
            'Могилевская область': ['Могилёв', 'Бобруйск', 'Горки', 'Осиповичи', 'Кричев', 'Быхов', 'Климовичи', 'Шклов', 'Костюковичи', 'Чаусы', 'Мстиславль', 'Белыничи', 'Кировск', 'Чериков', 'Славгород', 'Круглое', 'Кличев', 'Дрибин'],
            'Минск': ['Минск']
        }

        # Фильтрация по региону и городу
        if region:
            if city:
                # Если выбран конкретный город - фильтруем по нему
                query = query.filter(Articles.address.ilike(f"%{city}%"))
            else:
                # Если город не выбран - фильтруем по всем городам области
                cities_in_region = cities_by_region.get(region, [])
                if cities_in_region:
                    # Создаем условия для каждого города в области
                    region_filters = []
                    for city_name in cities_in_region:
                        region_filters.append(Articles.address.ilike(f"%{city_name}%"))
                    # Объединяем условия через OR
                    query = query.filter(or_(*region_filters))
        
        if category:
            query = query.filter(Articles.category == category)
        if min_price:
            query = query.filter(Articles.price >= int(min_price))
        if max_price:
            query = query.filter(Articles.price <= int(max_price))
        if type_app:
            query = query.filter(Articles.type_app == type_app)
        if available_date:
            query = query.filter(~Articles.orders.any(Orders.date == available_date))
        if count_rooms:
            if int(count_rooms) >= 4:
                query = query.filter(Articles.count_rooms >= int(count_rooms))
            else:
                query = query.filter(Articles.count_rooms == int(count_rooms))
            
        filtered_articles = query.all()
        
        return render_template("catalog.html",
            datetime=datetime,
            timedelta=timedelta,
            articles=filtered_articles,
            min_price_all=min_price_all,
            max_price_all=max_price_all,
            selected_region=region,
            selected_city=city
        )


@app.route('/card/<int:id>', methods=['GET', 'POST'])
def card(id):
    article = Articles.query.get(id)
    total_user = None
    if 'name' in session:
        total_user = Users.query.filter_by(email=session['name']).first()

    # Корректное условие с учетом приоритета операций
    if not article or (article.hide and (not total_user or (total_user.root != 1 and article.id_user != total_user.id))):
        abort(404)

    check = Orders.query.filter_by(id_article=article.id).all()
    images = Image.query.filter_by(article_id=id).all()
    if request.method == 'POST':
        article.title = request.form.get('title')
        article.category = request.form.get('category')
        article.address = request.form.get('address')
        article.type_app = request.form.get('type')
        article.price = request.form.get('price')
        article.text = request.form.get('ckeditor')
        article.floor = request.form.get('floor')
        article.entrance = request.form.get('entrance')
        article.count_rooms = request.form.get('count_rooms')
        image = request.files['image']
        if image:
            filename = secure_filename(image.filename)
            pic_name = str(uuid.uuid4()) + "_" + filename
            image.save("static/img/upload/" + pic_name)
            article.image_name = pic_name
        db.session.commit()
        flash("Запись обновлена!", category="ok")
        return redirect(url_for("card", id=article.id))
    return render_template("card.html",article=article,check=check,images=images)


@app.route('/about')
def about():
    return render_template("about.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    session.pop('name', None)
    if request.method == 'POST':
        email = request.form.get('email')
        password = md5(request.form.get('password').encode()).hexdigest()
        user = Users.query.filter_by(email=email,password=password).first()
        if user:
            session['name'] = Users.query.filter_by(email=email).first().email
            return redirect(url_for("index"))
        else:
            flash("Неправильная почта или пароль!", category="bad")
            return redirect(url_for("login"))
    return render_template("login.html")


@app.route('/reg', methods=['GET', 'POST'])
def reg():
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            surname = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            user = Users(name=name,surname=surname,email=email,password=md5(password.encode()).hexdigest())
            db.session.add(user)
            db.session.commit()
            flash("Регистрация прошла успешно!", category="ok")
            return redirect(url_for("reg"))
        except:
            flash("Произошла ошибка! Проверьте введенные данные!", category="bad")
            db.session.rollback()
            return redirect(url_for("reg"))
    return render_template("reg.html")


@app.route('/delete-article/<int:id>')
def delete_article(id):
    obj = Articles.query.filter_by(id=id).first()
    db.session.delete(obj)
    db.session.commit()
    flash("Запись удалена!", category="bad")
    message = f"Ваше объявление '{obj.title}' было удалено!"
    notification = Notification(
            user_id=obj.id_user,
            message=message,
            article_id=obj.id,
            is_read=False
        )
    db.session.add(notification)
    db.session.commit()
    return redirect('/catalog')


@app.route('/change-status/<int:id>', methods=['GET', 'POST'])
def change_article(id):
    if not 'name' in session:
        abort(401)
    
    article = Articles.query.get_or_404(id)
    current_user = Users.query.filter_by(email=session['name']).first()
    
    if article.id_user != current_user.id and current_user.root != 1:
        abort(403)
    
    if request.method == 'POST' and current_user.root == 1:
        # Это запрос от админа с причиной отклонения
        reason = request.form.get('reason', '')
        article.hide = True  # Оставляем на модерации
        
        notification = Notification(
            user_id=article.id_user,
            message=f"Ваше объявление '{article.title}' было отклонено модератором. Причина: {reason}",
            article_id=article.id,
            is_read=False
        )
        db.session.add(notification)
        db.session.commit()
        
        flash("Объявление отклонено с уведомлением пользователя", "ok")
        return redirect(url_for("card", id=id))
    
    # Запоминаем предыдущее состояние
    previous_status = article.hide
    
    # Меняем статус
    article.hide = not article.hide
    db.session.commit()
    
    # Создаем уведомление, если статус изменился и это не админ
    if current_user.root != 1:
        if previous_status:
            message = f"Ваше объявление '{article.title}' прошло модерацию и теперь видно всем пользователям"
        else:
            message = f"Ваше объявление '{article.title}' скрыто и больше не видно другим пользователям"
        
        notification = Notification(
            user_id=article.id_user,
            message=message,
            article_id=article.id,
            is_read=False
        )
        db.session.add(notification)
        db.session.commit()
    
    flash("Статус изменен!", category="ok")
    return redirect(url_for("card", id=id))


@app.route('/approve-article/<int:id>', methods=['POST'])
def approve_article(id):
    if not 'name' in session:
        abort(401)
    
    current_user = Users.query.filter_by(email=session['name']).first()
    if current_user.root != 1:
        abort(403)
    
    article = Articles.query.get_or_404(id)
    article.hide = False
    
    # Создаем уведомление для владельца
    notification = Notification(
        user_id=article.id_user,
        message=f"Ваше объявление '{article.title}' было одобрено и опубликовано",
        article_id=article.id,
        is_read=False
    )
    db.session.add(notification)
    db.session.commit()
    
    flash("Объявление одобрено и опубликовано", "ok")
    return redirect(url_for("card", id=id))

@app.route('/reject-article/<int:id>', methods=['POST'])
def reject_article(id):
    if not 'name' in session:
        abort(401)
    
    current_user = Users.query.filter_by(email=session['name']).first()
    if current_user.root != 1:
        abort(403)
    
    article = Articles.query.get_or_404(id)
    reason = request.form.get('reason', '')
    
    # Создаем уведомление для владельца с причиной
    notification = Notification(
        user_id=article.id_user,
        message=f"Ваше объявление '{article.title}' было отклонено. Причина: {reason}",
        article_id=article.id,
        is_read=False
    )
    db.session.add(notification)
    db.session.commit()
    
    flash("Объявление отклонено с уведомлением пользователя", "ok")
    return redirect(url_for("card", id=id))



@app.route('/delete-order/<int:id>')
def delete_order(id):
    obj = Orders.query.filter_by(id=id).first()
    db.session.delete(obj)
    db.session.commit()
    flash("Заказ отменен!", category="bad")
    return redirect('/profile')


@app.route('/add-order/<int:id_user>/<int:id_article>', methods=['POST'])
def add_order(id_user, id_article):
    if request.method == 'POST':
        article = Articles.query.get_or_404(id_article)
        selected_dates_json = request.form.get('selected_dates', '[]')
        
        try:
            selected_dates = json.loads(selected_dates_json)
            current_date = datetime.now().date()
            
            if not selected_dates:
                flash("Не выбрано ни одной даты!", category="bad")
                return redirect(url_for("card", id=id_article))
            
            for date_str in selected_dates:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
                
                if date < current_date:
                    flash(f"Дата {date_str} уже прошла!", category="bad")
                    continue
                
                existing_order = Orders.query.filter_by(
                    id_article=id_article,
                    date=date
                ).first()
                
                if existing_order:
                    flash(f"Дата {date_str} уже занята!", category="bad")
                    continue
                
                order = Orders(
                    date=date,
                    id_user=id_user,
                    id_article=id_article
                )
                db.session.add(order)
                
                # Создаем уведомление с флагом перенаправления в чат
                notification = Notification(
                user_id=article.id_user,  # Уведомление для владельца объявления
                message=f"Ваше жилье '{article.title}' забронировано на {date_str}",
                article_id=article.id,
                redirect_to_chat=True,
                chat_article_id=article.id,
                chat_user_id=id_user,  # ID арендатора
                is_read=False
            )
                db.session.add(notification)
            
            db.session.commit()
            flash("Бронирование оформлено!", category="ok")
            
        except ValueError:
            flash("Некорректный формат даты!", category="bad")
        except json.JSONDecodeError:
            flash("Ошибка обработки выбранных дат!", category="bad")
            
    return redirect(url_for("card", id=id_article))


@app.route('/get_available_dates/<int:article_id>')
def get_available_dates(article_id):
    article = Articles.query.get_or_404(article_id)
    if not article:
        return jsonify([])
    
    # Получаем забронированные даты
    booked_orders = Orders.query.filter_by(id_article=article_id).all()
    booked_dates = [order.date.date() for order in booked_orders if order.date]
    
    available_dates = []
    today = datetime.now().date()
    
    if article.type_app == "Посуточная":
        # Для посуточной - все даты на 3 месяца вперед, кроме забронированных
        for i in range(365):  # 12 месяца
            date = today + timedelta(days=i)
            if date not in booked_dates:
                available_dates.append(date.strftime('%Y-%m-%d'))
    else:
       # Для ежемесячной - только первые числа месяцев
        current_month = today.month
        current_year = today.year
        
        # Если сегодня уже не первое число, начинаем со следующего месяца
        if today.day > 1:
            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1
        
        for i in range(12):  # 12 месяца вперед
            month = current_month + i
            year = current_year
            if month > 12:
                month -= 12
                year += 1
            
            date = datetime(year, month, 1).date()
            if date not in booked_dates:
                available_dates.append(date.strftime('%Y-%m-%d'))
    
    return jsonify(available_dates)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(403)
def forbidded(e):
    return render_template('403.html'), 403


@app.errorhandler(401)
def forbidded(e):
    return render_template('401.html'), 401


@app.route('/logout')
def logout():
    session.pop('name', None)
    return redirect('/')


@app.context_processor
def inject_user():
    def get_user_name():
        if 'name' in session:
            return Users.query.filter_by(email=session['name']).first()
    return dict(active_user=get_user_name())


@app.route('/clear-notifications', methods=['GET'])
def clear_notifications():
    if not 'name' in session:
        abort(401)
    
    user = Users.query.filter_by(email=session['name']).first()
    # Удаляем все уведомления пользователя
    Notification.query.filter_by(user_id=user.id).delete()
    db.session.commit()
    
    flash("Все уведомления удалены", "ok")
    return redirect(url_for('profile'))


@app.context_processor
def inject_unread_count():
    if 'name' in session:
        user = Users.query.filter_by(email=session['name']).first()
        if user:
            unread_count = Notification.query.filter_by(user_id=user.id, is_read=False).count()
            return dict(unread_notifications=unread_count)
    return dict(unread_notifications=0)





@app.route('/edit_profile', methods=['POST'])
def edit_profile():
    if request.method == 'POST':
        total_user = Users.query.filter_by(email=session['name']).first()
        total_user.name = request.form.get('name')
        total_user.surname = request.form.get('surname')
        total_user.email = request.form.get('email')
        total_user.password = md5(request.form.get('password').encode()).hexdigest()
        db.session.commit()
        session.pop('name', None)
        session['name'] = request.form.get('email')
        flash("Данные обновлены!", category="ok")
    return redirect(url_for("profile"))


@app.route('/load_avatar', methods=['POST'])
def load_avatar():
    if request.method == 'POST':
        image = request.files['avatar']
        total_user = Users.query.filter_by(email=session['name']).first()
        filename = secure_filename(image.filename)
        pic_name = str(uuid.uuid4()) + "_" + filename
        image.save("static/img/upload/" + pic_name)
        total_user.avatar = pic_name
        db.session.commit()
        flash("Аватар обновлен!", category="ok")
        return redirect(url_for("profile"))


if __name__ == '__main__':
    app.run(debug=True)