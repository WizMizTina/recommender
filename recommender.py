# Contains parts from: https://flask-user.readthedocs.io/en/latest/quickstart_app.html

from flask import Flask, render_template, session, url_for, redirect
from flask_user import login_required, UserManager, current_user
from flask import request
from models import db, User, Movie, MovieGenre, Ratings
from read_data import check_and_read_data, check_and_read_data_tags, check_and_read_data_links, check_and_read_data_ratings

from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
from sqlalchemy import event
import random
from sklearn.metrics.pairwise import cosine_similarity

# Class-based application configuration
class ConfigClass(object):
    """ Flask application config """

    # Flask settings
    SECRET_KEY = 'This is an INSECURE secret!! DO NOT use this in production!!'

    # Flask-SQLAlchemy settings
    SQLALCHEMY_DATABASE_URI = 'sqlite:///movie_recommender.sqlite'  # File-based SQL database
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # Avoids SQLAlchemy warning

    # Flask-User settings
    USER_APP_NAME = "Movie Recommender"  # Shown in and email templates and page footers
    USER_ENABLE_EMAIL = False  # Disable email authentication
    USER_ENABLE_USERNAME = True  # Enable username authentication
    USER_REQUIRE_RETYPE_PASSWORD = True  # Simplify register form

# Use an event listener to set a unique user_id before insert
@event.listens_for(User, 'before_insert')
def before_user_insert(mapper, connection, target):
    target.id = random.randint(1000, 9000)

# Create Flask app
app = Flask(__name__)
app.config.from_object(__name__ + '.ConfigClass')  # configuration
app.app_context().push()  # create an app context before initializing db
db.init_app(app)  # initialize database
db.create_all()  # create database if necessary
user_manager = UserManager(app, db, User)  # initialize Flask-User management


@app.cli.command('initdb')
def initdb_command():
    global db
    """Creates the database tables."""
    check_and_read_data(db)
    check_and_read_data_tags(db)
    check_and_read_data_links(db)
    check_and_read_data_ratings(db)
    print('Initialized the database.')

# The Home page is accessible to anyone
@app.route('/')
def home_page():
    # render home.html template
    return render_template("home.html")

def get_current_user_id():
    return current_user.id

# The Members page is only accessible to authenticated users via the @login_required decorator
@app.route('/movies',methods=['GET', 'POST'])
@login_required  # User must be authenticated
def movies_page():
    # String-based templates
    all_genres = MovieGenre.query.distinct(MovieGenre.genre).all()
    genres= []
    for g in all_genres:
        if g.genre not in genres:
            genres.append(g.genre)
    if request.method == 'POST':
        selected_genres = request.form.getlist('selected_genres')
        #Filter movies based on selected genres
        movies = Movie.query.filter(Movie.genres.any(MovieGenre.genre.in_(selected_genres))).limit(100).all()
        session['selected_genres'] = selected_genres
    else:
        # Default behavior: Display the first 100 movies
        movies = Movie.query.limit(100).all()
    rated_movies = []
    for m in movies:
        rating_key = f'rating_{m.id}'
        rating_value = request.form.get(rating_key)
        if rating_value:
            rating_value = int(rating_value)
            rated_movies.append({'movie': m, 'rating': rating_value})
        else:
            rated_movies.append({'movie_id': m.id, 'rating': 'NA'})

    # Store rated_movies in the session for later use
    session['rated_movies'] = rated_movies

    return render_template("movies.html", movies=movies, genres = genres)


@app.route('/movies_results/', methods=['GET', 'POST'])
@login_required  # User must be authenticated
def show_movies_results():
    genres = session.get('selected_genres', [])

   #retrieve ratings
    ratings = {}
    for key, value in request.form.items():
        if key.startswith('rating_'):
            movie_id = int(key.split('_')[1])
            ratings[movie_id] = int(value)
    # Now, 'ratings' is a dictionary where keys are movie IDs and values are ratings

    #Store for later use
    session['rated_movies'] = ratings

    # Retrieve all movies
    movies = Movie.query.all()
    rated_titles = {}
    for movie in movies:
        # Get the titles of rated movies based on their IDs
        if movie.id in ratings.keys():
            rated_titles[movie.id]= movie.title
        
    #retrieve current user
    current_user_id = get_current_user_id()

    for movie_id, rating_value in ratings.items():
        # Check if the movie_id is valid (exists in the Movie table)
        movie = Movie.query.get(movie_id)
        if movie:
            # Insert or update the rating in the Ratings table
            rating = Ratings.query.filter_by(user_id=current_user_id, movie_id=movie_id).first()
            if rating:
                # If the rating already exists, update it
                rating.rating = int(rating_value)
            else:
                # If the rating doesn't exist, create a new entry
                new_rating = Ratings(user_id=current_user_id, movie_id=movie_id, rating=int(rating_value))
                db.session.add(new_rating)

    # Commit the changes to the database
    db.session.commit()

    all_ratings = Ratings.query.all()
    movie_genres = MovieGenre.query.all()

    # Create a DataFrame to store the ratings with users in forst column and movie ids as other columns
    ratings_df = pd.DataFrame(columns=['user_id'])

    # Get unique movie IDs
    movie_ids = set(rating.movie_id for rating in all_ratings)

    # Add movie ID columns to the DataFrame
    ratings_df = ratings_df.join(pd.DataFrame(columns=list(movie_ids)))

    # Set 'user_id' as the index for the DataFrame
    ratings_df.set_index('user_id', inplace=True)

    # Fill the DataFrame with ratings
    for rating in all_ratings:
        ratings_df.at[rating.user_id, rating.movie_id] = rating.rating

    current_user_ratings = ratings_df.loc[current_user_id].dropna()
    #Find movies reviewed by the current user
    movies_reviewed_by_current_user = current_user_ratings.index
    #Extract ratings for those movies from other users
    other_users_ratings = ratings_df[ratings_df.index != current_user_id][movies_reviewed_by_current_user]
    #Apply cosine similarity as a simple similarity measure
    similarity_matrix = cosine_similarity(other_users_ratings.fillna(0), current_user_ratings.fillna(0).values.reshape(1, -1))
    #Find most similar user
    most_similar_users = ratings_df.index[ratings_df.index != current_user_id][similarity_matrix.flatten().argsort()[-2:][::-1]]

    # Display the resulting DataFrame
    print(ratings_df.loc[most_similar_users])

    
    #Find movies in the selected genres that the current user has not seen
    unseen = []
    for g in genres:
        for mov in movie_genres:
            if mov.genre == g and mov.movie_id not in movies_reviewed_by_current_user :
                unseen.append(mov.movie_id)
    #locate the ratings from most similar user of the unseen movies
    most_similar_user_ratings = ratings_df.loc[most_similar_users]
    #get movie ids of only those titles rated favorably by most similar user
    recommendations = []
    for index, row in most_similar_user_ratings.iterrows():
        for movie_id in unseen:
            try:
                if row[movie_id] > 4:
                    recommendations.append(movie_id)
            except KeyError:
                continue
    #get titles of the recommendations
    recommended_movies = []
    for movie in movies:
        # Get the titles of rated movies based on their IDs
        if movie.id in recommendations:
            recommended_movies.append(movie.title)
  
    #Locate the recommedations in the database
    rec_movies = Movie.query.filter(Movie.id.in_(recommendations)).all()

    print("Recommendations created successfully!")

    return render_template("movies_results.html", genres=genres, rated_movies=rated_titles.values(), rec_movies= rec_movies )

# Start development web server
if __name__ == '__main__':
    app.run(port=5000, debug=True)
