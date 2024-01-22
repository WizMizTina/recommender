# Contains parts from: https://flask-user.readthedocs.io/en/latest/quickstart_app.html

from flask import Flask, render_template, session, url_for, redirect
from flask_user import login_required, UserManager, current_user
from flask import request
from models import db, User, Movie, MovieGenre, Ratings
from read_data import check_and_read_data, check_and_read_data_tags, check_and_read_data_links, check_and_read_data_ratings
import requests
from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import TfidfVectorizer
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
    # Replace this with your actual implementation to get the current user ID
    # For example, if you are using Flask-Login:
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
        print(selected_genres)
        # You can modify the query to filter movies based on selected genres
        movies = Movie.query.filter(Movie.genres.any(MovieGenre.genre.in_(selected_genres))).limit(10).all()
        #movies = Movie.query.limit(10).all()
        session['selected_genres'] = selected_genres
    else:
        # Default behavior: Display the first 10 movies
        movies = Movie.query.limit(10).all()
    rated_movies = []
    for m in movies:
        rating_key = f'rating_{m.id}'
        rating_value = request.form.get(rating_key)
        #print(m.id, rating_value)
        if rating_value:
            rating_value = int(rating_value)
            rated_movies.append({'movie': m, 'rating': rating_value})
        else:
            rated_movies.append({'movie_id': m.id, 'rating': 'NA'})

    # Store rated_movies in the session for later use
    #session['movies']= movies
    session['rated_movies'] = rated_movies

    #Handle ratings
    


    # only Romance movies
    # movies = Movie.query.filter(Movie.genres.any(MovieGenre.genre == 'Romance')).limit(10).all()

    # only Romance AND Horror movies
    # movies = Movie.query\
    #     .filter(Movie.genres.any(MovieGenre.genre == 'Romance')) \
    #     .filter(Movie.genres.any(MovieGenre.genre == 'Horror')) \
    #     .limit(10).all()

    return render_template("movies.html", movies=movies, genres = genres)




@app.route('/movies_results/', methods=['GET', 'POST'])
@login_required  # User must be authenticated
def show_movies_results():
    genres = session.get('selected_genres', [])

    ratings = {}
    for key, value in request.form.items():
        if key.startswith('rating_'):
            movie_id = int(key.split('_')[1])
            ratings[movie_id] = int(value)

    # Now, 'ratings' is a dictionary where keys are movie IDs and values are ratings
    # You can use this dictionary to process and store the ratings as needed

    # Example: Print the ratings for demonstration
    for movie_id, rating in ratings.items():
        print(f'Movie ID: {movie_id}, Rating: {rating}')

    session['rated_movies'] = ratings

    # Retrieve all movies
    movies = Movie.query.all()
    rated_titles = {}
    for movie in movies:
        # Get the titles of rated movies based on their IDs
        if movie.id in ratings.keys():
            rated_titles[movie.id]= movie.title
        

    # Example: Print the titles of rated movies
    for movie_id, title in rated_titles.items():
        print(f'Movie ID: {movie_id}, Title: {title}, Rating: {ratings[movie_id]}')

    current_user_id = get_current_user_id()
    print("to db for", current_user_id)

    # Assuming you have a dictionary like ratings[movie_id] = int(value)

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

    # Create a DataFrame to store the ratings
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
    # Apply cosine similarity as a simple similarity measure
    print(current_user_ratings)
    print(other_users_ratings)
    similarity_matrix = cosine_similarity(other_users_ratings.fillna(0), current_user_ratings.fillna(0).values.reshape(1, -1))
    
    most_similar_users = ratings_df.index[ratings_df.index != current_user_id][similarity_matrix.flatten().argsort()[-1:][::-1]]

    # Display the resulting DataFrame
    print(ratings_df.loc[most_similar_users])

    

    # Display the resulting DataFrame
    print(current_user_id)
    #Find movies in the selected genres that the current user has not seen
    unseen = []
    for g in genres:
        for mov in movie_genres:
            if mov.genre == g and mov.movie_id not in movies_reviewed_by_current_user :
                unseen.append(mov.movie_id)

    most_similar_user_ratings = ratings_df.loc[most_similar_users]

    recommendations = []
    for index, row in most_similar_user_ratings.iterrows():
        for movie_id in unseen:
            try:
                if row[movie_id] > 4:
                    recommendations.append(movie_id)
            except KeyError:
                continue
    recommended_movies = []
    for movie in movies:
        # Get the titles of rated movies based on their IDs
        if movie.id in recommendations:
            recommended_movies.append(movie.title)
    # Display the resulting recommendations
    print(recommended_movies)

    print("Ratings submitted successfully")


    return render_template("movies_results.html", genres=genres, rated_movies=rated_titles, recommended_movies= recommended_movies )





# Route for submitting ratings
@app.route('/submit_ratings', methods=['POST'])
def submit_ratings():
    current_user_id = get_current_user_id()
    print("to db")

    # Assuming you have a dictionary like ratings[movie_id] = int(value)
    ratings = session.get('rated_movies', {})  # Adjust based on your actual form data structure

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

    # Query all ratings from the database
    all_ratings = Ratings.query.all()
    print(all_ratings)
    ratings_df_long = pd.read_csv("data/ratings.csv")
    ratings_df_long = pd.DataFrame(ratings_df_long.groupby('movie_id')['rating'].mean())
    print(ratings_df_long.head(5))
    # Create a DataFrame to store the ratings
    ratings_df = pd.DataFrame(columns=['user_id'])

    # Get unique movie IDs
    movie_ids = set(rating.movie_id for rating in all_ratings)

    # Add movie ID columns to the DataFrame
    ratings_df = ratings_df.join(pd.DataFrame(columns=movie_ids))

    # Set 'user_id' as the index for the DataFrame
    ratings_df.set_index('user_id', inplace=True)

    # Fill the DataFrame with ratings
    for rating in all_ratings:
        ratings_df.at[rating.user_id, rating.movie_id] = rating.rating

    # Display the resulting DataFrame
    #print(ratings_df)
    db.session.commit()

    return "Ratings submitted successfully"

# Start development web server
if __name__ == '__main__':
    app.run(port=5000, debug=True)
