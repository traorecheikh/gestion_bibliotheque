from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from functools import wraps
import os


app = Flask(__name__)
app.config.from_object('config.Config')
app.config['SECRET_KEY'] = os.environ.get('SQLALCHEMY_SECRET_KEY')
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/IMAGE')
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'connexion'


'''mot de passe admin = @admin et username = admin'''
class Utilisateur(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    nom_utilisateur = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    adresse = db.Column(db.String(120), nullable=False)
    mot_de_passe = db.Column(db.String(60), nullable=False)
    is_SuperUser = db.Column(db.Boolean, default=False)

    def is_active(self):
        return True

    def get_id(self):
        return str(self.id)


class Livre(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(100), nullable=False)
    auteur = db.Column(db.String(100), nullable=False)
    genre = db.Column(db.String(50), nullable=False)
    annee_publication = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=True)
    quantite = db.Column(db.Integer, default=1, nullable=False)
    image_url = db.Column(db.String(200), nullable=True)
    emprunts = db.relationship('Emprunt', backref='livre', lazy=True)


class Emprunt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateur.id'), nullable=False)
    livre_id = db.Column(db.Integer, db.ForeignKey('livre.id'), nullable=False)
    date_emprunt = db.Column(db.DateTime, nullable=False)
    duree_emprunt = db.Column(db.Integer, nullable=False)
    date_retour = db.Column(db.DateTime)


@login_manager.user_loader
def load_user(user_id):
    return Utilisateur.query.get(int(user_id))


def role_required(is_SuperUser_required):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('connexion'))
            if is_SuperUser_required and not current_user.is_SuperUser:
                return redirect(url_for('accueil'))
            if not is_SuperUser_required and current_user.is_SuperUser:
                return redirect(url_for('accueil_admin'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('accueil'))
    else:
        return redirect(url_for('connexion'))


@app.route('/gererUtilisateurs')
@login_required
@role_required(is_SuperUser_required=True)
def gererUtilisateurs():
    if current_user.is_SuperUser:
        utilisateurs = Utilisateur.query.all()
        return render_template('gerer_utilisateur.html', utilisateurs=utilisateurs)
    else:
        return redirect(url_for('accueil'))
    
    
@app.route('/supprimerUtilisateur/<int:id>', methods=['POST'])
@login_required
@role_required(is_SuperUser_required=True)
def supprimerUtilisateur(id):
    if not current_user.is_SuperUser:
        return redirect(url_for('accueil'))

    utilisateur = Utilisateur.query.get(id)
    if utilisateur:
        db.session.delete(utilisateur)
        db.session.commit()
        flash('Utilisateur supprimé avec succès.', 'success')
    else:
        flash('Utilisateur introuvable.', 'error')

    return redirect(url_for('gererUtilisateurs'))


@app.route('/connexion', methods=['GET', 'POST'])
def connexion():
    if current_user.is_authenticated:
        return redirect(url_for('accueil'))
    if request.method == 'POST':
        nom_utilisateur = request.form['nom_utilisateur']
        mot_de_passe = request.form['mot_de_passe']
        utilisateur = Utilisateur.query.filter_by(nom_utilisateur=nom_utilisateur).first()
        if utilisateur:
            if check_password_hash(utilisateur.mot_de_passe, mot_de_passe):
                login_user(utilisateur)
                flash('Connecté avec succès.', 'success')
                if utilisateur.is_SuperUser:
                    return redirect(url_for('accueil_admin'))
                else:
                    return redirect(url_for('accueil'))
            else:
                flash('Mot de passe incorrect.', 'error')
        else:
            flash('Nom d\'utilisateur inconnu.', 'error')
            return redirect(url_for('connexion'))
    return render_template('connexion.html')


@app.route('/inscription', methods=['GET', 'POST'])
def inscription():
    if current_user.is_authenticated:
        return redirect(url_for('accueil'))
    if request.method == 'POST':
        nom_utilisateur = request.form['nom_utilisateur']
        email = request.form['email']
        adresse = request.form['adresse']
        mot_de_passe = request.form['mot_de_passe']
        try:
            utilisateur_existant = Utilisateur.query.filter_by(nom_utilisateur=nom_utilisateur).first()
        except UnicodeError as e:
            flash('Erreur lors de l\'inscription. Veuillez réessayer.', 'error')
            return redirect(url_for('inscription'))
        if utilisateur_existant:
            flash('Nom d\'utilisateur déjà utilisé. Veuillez en choisir un autre.', 'error')
        else:
            nouveau_utilisateur = Utilisateur(nom_utilisateur=nom_utilisateur, email=email, adresse=adresse, mot_de_passe=generate_password_hash(mot_de_passe))
            db.session.add(nouveau_utilisateur)
            db.session.commit()
            flash('Compte créé avec succès. Vous pouvez maintenant vous connecter.', 'success')
            return redirect(url_for('connexion'))
    return render_template('inscription.html')


@app.route('/deconnexion')
@login_required
def deconnexion():
    logout_user()
    flash('Déconnecté avec succès.', 'success')
    return redirect(url_for('connexion'))


@app.route('/accueil')
@login_required
@role_required(is_SuperUser_required=False)
def accueil():
    '''
    je voulais ajouter ladmin directe dans la base a la premiere instanciation de la page accueil.
    admin_user = Utilisateur(nom_utilisateur="admin", email="admin@example.com",adresse="@admin", mot_de_passe=generate_password_hash("@admin"), is_SuperUser=True)
    db.session.add(admin_user)
    db.session.commit()'''
    return render_template('accueil.html')


@app.route('/accueil_admin')
@login_required
@role_required(is_SuperUser_required=True)
def accueil_admin():
        return render_template('accueil_admin.html')


@app.route('/bibliotheque')
@login_required
@role_required(is_SuperUser_required=False)
def bibliotheque():
    search = request.args.get('search')
    if search:
        livres = Livre.query.filter(
            (Livre.titre.ilike(f'%{search}%')) |
            (Livre.auteur.ilike(f'%{search}%'))|
            (Livre.genre.ilike(f'%{search}%'))
        ).all()
    else:
        livres = Livre.query.all()
    return render_template('bibliotheque.html', livres=livres)


@app.route('/ajout_livre', methods=['GET', 'POST'])
@login_required
@role_required(is_SuperUser_required=True)
def ajout_livre():

    if request.method == 'POST':
        try:
            titre = request.form['titre']
            auteur = request.form['auteur']
            genre = request.form['genre']
            annee_publication = request.form['annee_publication']
            description = request.form['description']
            quantite = request.form['quantite']

            image = request.files['image']
            if image:
                filename = secure_filename(image.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image.save(image_path)
                image_url = url_for('static', filename='IMAGE/' + filename)
            else:
                image_url = None

            new_livre = Livre(
                titre=titre,
                auteur=auteur,
                genre=genre,
                annee_publication=int(annee_publication),
                description=description,
                quantite=int(quantite),
                image_url=image_url
            )
            db.session.add(new_livre)
            db.session.commit()
            flash('Livre ajouté avec succès!', 'success')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Error adding book: {e}')
            flash('Erreur lors de l\'ajout du livre.', 'danger')

        return redirect(url_for('gerer_livres'))

    return render_template('ajouterlivre.html')


@app.route('/details_livre/<int:id>')
@login_required
@role_required(is_SuperUser_required=False)
def details_livre(id):
    livre = Livre.query.get(id)
    if not livre:
        flash('Livre introuvable.', 'error')
        return redirect(url_for('bibliotheque'))

    return render_template('details_livre.html', livre=livre)


@app.route('/gerer_livres')
@login_required
@role_required(is_SuperUser_required=True)
def gerer_livres():
    if not current_user.is_SuperUser:
        return redirect(url_for('accueil'))

    search = request.args.get('search')
    if search:
        livres = Livre.query.filter(
            (Livre.titre.ilike(f'%{search}%')) |
            (Livre.auteur.ilike(f'%{search}%'))|
            (Livre.genre.ilike(f'%{search}%'))
        ).all()
    else:
        livres = Livre.query.all()
    return render_template('gerer_livres.html', livres=livres)


@app.route('/supprimer_livre/<int:id>', methods=['POST'])
@login_required
@role_required(is_SuperUser_required=True)
def supprimer_livre(id):

    livre = Livre.query.get(id)
    if livre:
        db.session.delete(livre)
        db.session.commit()
        flash('Livre supprimé avec succès.', 'success')
    else:
        flash('Livre introuvable.', 'error')

    return redirect(url_for('gerer_livres'))


@app.route('/modifier_livre/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required(is_SuperUser_required=True)
def modifier_livre(id):

    livre = Livre.query.get(id)
    if request.method == 'POST':
        livre.titre = request.form['titre']
        livre.auteur = request.form['auteur']
        livre.genre = request.form['genre']
        livre.annee_publication = request.form['annee_publication']
        livre.quantite = request.form['quantite']
        livre.image_url = request.form['image_url']

        db.session.commit()
        flash('Livre modifié avec succès.', 'success')
        return redirect(url_for('gerer_livres'))

    return render_template('modifier_livre.html', livre=livre)


@app.route('/emprunter/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required(is_SuperUser_required=False)
def emprunter(id):
    date_emprunt = datetime.now()

    livre = Livre.query.get(id)
    if request.method == 'POST':
        livre.quantite -= 1

        nouvel_emprunt = Emprunt(
            utilisateur_id=current_user.id,
            livre_id=livre.id,
            date_emprunt=date_emprunt,
            duree_emprunt=15,
            date_retour=None
        )
        db.session.add(nouvel_emprunt)
        db.session.commit()

        flash('Emprunt effectué avec succès.', 'success')
        return redirect(url_for('mes_emprunts'))

    return render_template('emprunts.html', livre=livre, date_emprunt=date_emprunt.strftime('%d-%m-%Y'))


@app.route('/mes_emprunts')
@login_required
@role_required(is_SuperUser_required=False)
def mes_emprunts():
    emprunts = Emprunt.query.filter_by(utilisateur_id=current_user.id).all()
    return render_template('mes_emprunts.html', emprunts=emprunts)


@app.route('/retour_emprunt/<int:id>')
@login_required
@role_required(is_SuperUser_required=False)
def retour_emprunt(id):
    emprunt = Emprunt.query.get(id)
    if emprunt:
        emprunt.date_retour = datetime.now()
        livre_emprunte = emprunt.livre
        livre_emprunte.quantite += 1
        db.session.commit()
        flash('Livre retourné avec succès.', 'success')
    else:
        flash('Emprunt introuvable.', 'error')
    return redirect(url_for('mes_emprunts'))
    
    
@app.route('/voir_emprunts/<int:id>')
@login_required
@role_required(is_SuperUser_required=True)
def voir_emprunts(id):
    utilisateur = Utilisateur.query.get(id)
    emprunts = Emprunt.query.filter_by(utilisateur_id=id).all()
    return render_template('voir_emprunts.html', utilisateur=utilisateur, emprunts=emprunts)


if __name__ == '__main__':
    app.run(debug=True)
