import os
import shutil
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message as MailMessage
from datetime import datetime

# --- Imports pour Cloudinary ---
import cloudinary
import cloudinary.uploader
import cloudinary.api

app = Flask(__name__)

# CONFIGURATION
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Utilisation des variables d'environnement pour la sécurité (Render les gérera)
app.secret_key = os.environ.get('SECRET_KEY', 'une_cle_tres_secrete_et_compliquee_a_changer')

# CONFIGURATION EMAIL (Forçage de la langue FR pour les emails)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'votre.email@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'votre_mot_de_passe_app')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME', 'votre.email@gmail.com')

# --- Configuration Cloudinary ---
cloudinary.config(
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key = os.environ.get('CLOUDINARY_API_KEY'),
    api_secret = os.environ.get('CLOUDINARY_API_SECRET')
)

db = SQLAlchemy(app)
mail = Mail(app)

# --- TABLES DE LA BASE DE DONNÉES ---
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    contenu = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    statut = db.Column(db.String(20), default="Non lu")
    client_id = db.Column(db.String(100), nullable=True)

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(200), nullable=False)
    contenu = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)

class Media(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(200), nullable=False)
    type_fichier = db.Column(db.String(50), nullable=False)  # 'image' ou 'pdf'
    url_fichier = db.Column(db.String(500), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    auteur = db.Column(db.String(100), nullable=False)
    contenu = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'), nullable=False)
    article = db.relationship('Article', backref=db.backref('comments', lazy=True))

class ClientLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_connexion = db.Column(db.DateTime, default=datetime.utcnow)

# ✅ SCRIPT DE NETTOYAGE ULTIME AU DÉMARRAGE
with app.app_context():
    if os.path.exists('site.db'):
        os.remove('site.db')
        print("🔴 Ancienne base de données supprimée avec succès !")
    
    if os.path.exists('__pycache__'):
        shutil.rmtree('__pycache__')
        print("🔴 Cache Python supprimé avec succès !")
    
    db.create_all()
    print("🟢 Nouvelle base de données créée avec succès !")

# --- PAGES PUBLIQUES ---
@app.route('/')
def home():
    articles = Article.query.order_by(Article.date.desc()).limit(3).all()
    medias = Media.query.order_by(Media.date.desc()).limit(3).all()
    
    return render_template('index.html', 
                           titre="Accueil - Allen Smith Group", 
                           meta_description="Découvrez Allen Smith Group, votre partenaire pour vos projets web et technologiques.",
                           articles=articles,
                           medias=medias)

@app.route('/about')
def about():
    return render_template('about.html', titre="À propos - Allen Smith Group", meta_description="Découvrez l'histoire et les valeurs d'Allen Smith Group, votre partenaire technologique de confiance.")

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        nom = request.form.get('nom')
        email = request.form.get('email')
        message_texte = request.form.get('message')
        
        nouveau_message = Message(nom=nom, email=email, contenu=message_texte, client_id=email)
        db.session.add(nouveau_message)
        db.session.commit()

        try:
            msg = MailMessage(
                subject='Nouveau message sur Allen Smith Group',
                sender=app.config['MAIL_DEFAULT_SENDER'],
                recipients=[app.config['MAIL_DEFAULT_SENDER']]
            )
            msg.body = f"Vous avez reçu un message de {nom} ({email}).\n\nMessage :\n{message_texte}"
            mail.send(msg)
        except Exception as e:
            print(f"Erreur lors de l'envoi de l'email : {e}")

        return redirect(url_for('merci', nom=nom))
 
    return render_template('contact.html', titre="Contact - Allen Smith Group", meta_description="Contactez Allen Smith Group pour vos projets web et technologiques.")

@app.route('/merci')
def merci():
    nom = request.args.get('nom')
    return render_template('merci.html', titre="Message envoyé", nom=nom)

@app.route('/blog')
def blog():
    articles = Article.query.order_by(Article.date.desc()).limit(10).all()
    return render_template('blog.html', titre="Actualités - Allen Smith Group", articles=articles, meta_description="Suivez les dernières actualités et innovations d'Allen Smith Group.")

@app.route('/article/<int:id>')
def article_detail(id):
    article = Article.query.get_or_404(id)
    return render_template('article_detail.html', titre=article.titre, article=article, meta_description="Lisez notre article : " + article.titre)

@app.route('/user/<username>')
def user(username):
    return render_template('user.html', titre=f"Profil de {username}", username=username)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', titre="Page introuvable"), 404

# --- TÉLÉCHARGEMENT DE FICHIERS (PDF) ---
@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory('static', filename)

# ✅ ROUTES MANQUANTES AJOUTÉES ICI
@app.route('/legal')
def legal():
    return render_template('legal.html', titre="Mentions légales")

@app.route('/faq')
def faq():
    return render_template('faq.html', titre="FAQ")

@app.route('/testimonials')
def testimonials():
    return render_template('testimonials.html', titre="Témoignages")

# --- PARTIE CONNEXION UNIQUE ---
ADMIN_PASSWORD = "Allen2026" 
CLIENT_PASSWORD = "Client2026"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin'))
    if session.get('client_logged_in'):
        return redirect(url_for('client_dashboard'))
    
    if request.method == 'POST':
        password_attempt = request.form.get('password')
        
        if password_attempt == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        elif password_attempt == CLIENT_PASSWORD:
            session['client_logged_in'] = True
            nouveau_log = ClientLog()
            db.session.add(nouveau_log)
            db.session.commit()
            return redirect(url_for('client_dashboard'))
        else:
            return render_template('login.html', titre="Connexion", error="Mot de passe incorrect !")
            
    return render_template('login.html', titre="Connexion")

# --- PARTIE ADMINISTRATION ---
@app.route('/admin')
def admin():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    
    messages = Message.query.order_by(Message.date.desc()).all()
    articles = Article.query.order_by(Article.date.desc()).limit(10).all()
    medias = Media.query.order_by(Media.date.desc()).limit(10).all()
    total_connexions = ClientLog.query.count()
    dernieres_connexions = ClientLog.query.order_by(ClientLog.date_connexion.desc()).limit(5).all()
    unread_count = Message.query.filter_by(statut="Non lu").count()
    
    return render_template('admin.html', titre="Administration", 
                           messages=messages, articles=articles, medias=medias,
                           total_connexions=total_connexions, 
                           dernieres_connexions=dernieres_connexions,
                           unread_count=unread_count)

@app.route('/admin/new_article', methods=['GET', 'POST'])
def new_article():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        titre = request.form.get('titre')
        contenu = request.form.get('contenu')
        
        image_url = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                try:
                    upload_result = cloudinary.uploader.upload(file)
                    image_url = upload_result['secure_url']
                    print(f"✅ Image uploadée avec succès : {image_url}")
                except Exception as e:
                    print(f"❌ Erreur upload image : {e}")
        
        nouvel_article = Article(titre=titre, contenu=contenu, image_url=image_url)
        db.session.add(nouvel_article)
        db.session.commit()
        return redirect(url_for('admin'))
        
    return render_template('new_article.html', titre="Publier un article")

@app.route('/admin/message/<int:id>', methods=['GET', 'POST'])
def view_message(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    
    msg = Message.query.get_or_404(id)
    if msg.statut == "Non lu":
        msg.statut = "En cours"
        db.session.commit()
    
    if request.method == 'POST':
        reponse_texte = request.form.get('reponse')
        msg.statut = "✅ Traité"
        db.session.commit()
        
        try:
            msg_reponse = MailMessage(
                subject='Réponse de Allen Smith Group',
                sender=app.config['MAIL_DEFAULT_SENDER'],
                recipients=[msg.email]
            )
            msg_reponse.body = f"Bonjour {msg.nom},\n\nVoici la réponse de l'équipe Allen Smith Group à votre message :\n\n{reponse_texte}\n\nCordialement,\nL'équipe Allen Smith Group"
            mail.send(msg_reponse)
            reponse_envoye = True
        except Exception as e:
            print(f"Erreur lors de l'envoi de la réponse : {e}")
            reponse_envoye = False
        
        return render_template('view_message.html', titre=f"Message de {msg.nom}", message=msg, reponse_envoye=reponse_envoye)
    
    return render_template('view_message.html', titre=f"Message de {msg.nom}", message=msg)

@app.route('/admin/delete_article/<int:id>')
def delete_article(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    
    article = Article.query.get_or_404(id)
    db.session.delete(article)
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/new_media', methods=['GET', 'POST'])
def new_media():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        titre = request.form.get('titre')
        type_fichier = request.form.get('type_fichier')
        
        url_fichier = None
        if 'fichier' in request.files:
            file = request.files['fichier']
            if file and file.filename != '':
                try:
                    upload_result = cloudinary.uploader.upload(file, resource_type="auto")
                    url_fichier = upload_result['secure_url']
                    print(f"✅ Fichier uploadé avec succès : {url_fichier}")
                except Exception as e:
                    print(f"❌ Erreur upload : {e}")
        
        if url_fichier:
            nouveau_media = Media(titre=titre, type_fichier=type_fichier, url_fichier=url_fichier)
            db.session.add(nouveau_media)
            db.session.commit()
            return redirect(url_for('admin'))
        
    return render_template('new_media.html', titre="Publier un média")

@app.route('/article/<int:id>/comment', methods=['POST'])
def add_comment(id):
    article = Article.query.get_or_404(id)
    auteur = request.form.get('auteur')
    contenu = request.form.get('contenu')
    
    nouveau_commentaire = Comment(auteur=auteur, contenu=contenu, article=article)
    db.session.add(nouveau_commentaire)
    db.session.commit()
    
    return redirect(url_for('article_detail', id=id))

@app.route('/media_library')
def media_library():
    medias = Media.query.order_by(Media.date.desc()).all()
    return render_template('media_library.html', titre="Bibliothèque", medias=medias)

@app.route('/client_messages')
def client_messages():
    if not session.get('client_logged_in'):
        return redirect(url_for('login'))
    
    email = request.args.get('email')
    messages = []
    if email:
        messages = Message.query.filter_by(client_id=email).order_by(Message.date.desc()).all()
    
    return render_template('client_messages.html', titre="Mes Messages", messages=messages)

@app.route('/client_dashboard')
def client_dashboard():
    if not session.get('client_logged_in'):
        return redirect(url_for('login'))
    return render_template('client_dashboard.html', titre="Espace Client")

@app.route('/force_update')
def force_update():
    return "Mise à jour forcée effectuée. Les routes FAQ, Témoignages et Mentions légales sont maintenant actives."

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    session.pop('client_logged_in', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)