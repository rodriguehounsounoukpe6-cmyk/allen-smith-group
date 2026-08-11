import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message as MailMessage
from datetime import datetime

app = Flask(__name__)

# CONFIGURATION
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Utilisation des variables d'environnement pour la sécurité (Render les gérera)
app.secret_key = os.environ.get('SECRET_KEY', 'une_cle_tres_secrete_et_compliquee_a_changer')

# CONFIGURATION EMAIL
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'votre.email@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'votre_mot_de_passe_app')

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
    # ✅ NOUVEAU CHAMP POUR L'IMAGE
    image_url = db.Column(db.String(500), nullable=True) 
    date = db.Column(db.DateTime, default=datetime.utcnow)

class ClientLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_connexion = db.Column(db.DateTime, default=datetime.utcnow)

# --- CRÉATION DES TABLES ---
with app.app_context():
    db.create_all()

# --- PAGES PUBLIQUES ---
@app.route('/')
def home():
    return render_template('index.html', titre="Accueil - Allen Smith Group")

@app.route('/about')
def about():
    return render_template('about.html', titre="À propos - Allen Smith Group")

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
            msg = MailMessage('Nouveau message sur Allen Smith Group',
                              sender=app.config['MAIL_USERNAME'],
                              recipients=[app.config['MAIL_USERNAME']])
            msg.body = f"Vous avez reçu un message de {nom} ({email}).\n\nMessage :\n{message_texte}"
            mail.send(msg)
        except Exception as e:
            print(f"Erreur lors de l'envoi de l'email : {e}")

        return render_template('merci.html', titre="Message envoyé", nom=nom)

    return render_template('contact.html', titre="Contact - Allen Smith Group")

@app.route('/blog')
def blog():
    articles = Article.query.order_by(Article.date.desc()).all()
    return render_template('blog.html', titre="Actualités - Allen Smith Group", articles=articles)

@app.route('/article/<int:id>')
def article_detail(id):
    article = Article.query.get_or_404(id)
    return render_template('article_detail.html', titre=article.titre, article=article)

@app.route('/user/<username>')
def user(username):
    return render_template('user.html', titre=f"Profil de {username}", username=username)

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
    articles = Article.query.order_by(Article.date.desc()).all()
    total_connexions = ClientLog.query.count()
    dernieres_connexions = ClientLog.query.order_by(ClientLog.date_connexion.desc()).limit(5).all()
    
    return render_template('admin.html', titre="Administration", 
                           messages=messages, articles=articles,
                           total_connexions=total_connexions, 
                           dernieres_connexions=dernieres_connexions)

@app.route('/admin/new_article', methods=['GET', 'POST'])
@app.route('/admin/new_article', methods=['GET', 'POST'])
def new_article():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        titre = request.form.get('titre')
        contenu = request.form.get('contenu')
        # ✅ NOUVEAU : On récupère le lien de l'image
        image_url = request.form.get('image_url')
        
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
        return render_template('view_message.html', titre=f"Message de {msg.nom}", message=msg, reponse_envoye=True)
    
    return render_template('view_message.html', titre=f"Message de {msg.nom}", message=msg)

@app.route('/admin/delete_article/<int:id>')
def delete_article(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    
    article = Article.query.get_or_404(id)
    db.session.delete(article)
    db.session.commit()
    return redirect(url_for('admin'))

# --- HISTORIQUE CLIENT ---
@app.route('/client_messages')
def client_messages():
    if not session.get('client_logged_in'):
        return redirect(url_for('login'))
    
    email = request.args.get('email')
    messages = []
    if email:
        messages = Message.query.filter_by(client_id=email).order_by(Message.date.desc()).all()
    
    return render_template('client_messages.html', titre="Mes Messages", messages=messages)

# --- PARTIE CLIENT ---
@app.route('/client_dashboard')
def client_dashboard():
    if not session.get('client_logged_in'):
        return redirect(url_for('login'))
    return render_template('client_dashboard.html', titre="Espace Client")

# --- DÉCONNEXION UNIQUE ---
@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    session.pop('client_logged_in', None)
    return redirect(url_for('home'))

# --- LANCEMENT DU SERVEUR (SANS DEBUG POUR LA PRODUCTION) ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)