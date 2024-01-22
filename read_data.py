import csv
from sqlalchemy.exc import IntegrityError
from models import Movie, MovieGenre, Tags, Links, Ratings
from datetime import datetime

def check_and_read_data(db):
    # check if we have movies in the database
    # read data if database is empty
    if Movie.query.count() == 0:
        # read movies from csv
        with open('data/movies.csv', newline='', encoding='utf8') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            count = 0
            for row in reader:
                if count > 0:
                    try:
                        id = row[0]
                        title = row[1]
                        movie = Movie(id=id, title=title)
                        db.session.add(movie)
                        genres = row[2].split('|')  # genres is a list of genres
                        for genre in genres:  # add each genre to the movie_genre table
                            movie_genre = MovieGenre(movie_id=id, genre=genre)
                            db.session.add(movie_genre)
                        db.session.commit()  # save data to database
                    except IntegrityError:
                        print("Ignoring duplicate movie: " + title)
                        db.session.rollback()
                        pass
                count += 1
                if count % 100 == 0:
                    print(count, " movies read")

def check_and_read_data_tags(db):
    # check if we have movies in the database
    # read data if database is empty
    if Tags.query.count() == 0:
        # read tags from csv
        with open('data/tags.csv', newline='', encoding='utf8') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            count = 0
            for row in reader:
                if count > 0:
                    try:
                        id = row[1]
                        tag = row[2]
                        movie_id = id
                        timestamp = datetime.fromtimestamp(int(row[3]))
                        tags = Tags(id=id,movie_id = movie_id, tag= tag, timestamp= timestamp)
                        db.session.add(tags)
                        db.session.commit()  # save data to database
                    except IntegrityError:
                        print("Ignoring duplicate movie: " + id)
                        db.session.rollback()
                        pass
                count += 1
                if count % 100 == 0:
                    print(count, " movies read")


def check_and_read_data_links(db):
    # check if we have movies in the database
    # read data if database is empty
    if Links.query.count() == 0:
        # read tags from csv
        with open('data/links.csv', newline='', encoding='utf8') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            count = 0
            for row in reader:
                if count > 0:
                    try:
                        id = row[0]
                        movie_id = id
                        imdb_id = row[1]
                        tmdb_id = row[2]
                        links = Links(id= id, movie_id= movie_id, imdb_id= imdb_id, tmdb_id= tmdb_id)
                        db.session.add(links)
                        db.session.commit()  # save data to database
                    except IntegrityError:
                        print("Ignoring duplicate movie: " + movie_id)
                        db.session.rollback()
                        pass
                count += 1
                if count % 100 == 0:
                    print(count, " movies read")

def check_and_read_data_ratings(db):
    # check if we have movies in the database
    # read data if database is empty
    if Ratings.query.count() == 0:
        # read tags from csv
        with open('data/ratings.csv', newline='', encoding='utf8') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            count = 0
            for row in reader:
                if count > 0:
                    try:
                        id = row[1]
                        movie_id = id
                        user_id = row[0]
                        rating = row[2]
                        ratings = Ratings(id= id, user_id= user_id, movie_id= movie_id,  rating= rating)
                        db.session.add(ratings)
                        db.session.commit()  # save data to database
                    except IntegrityError:
                        print("Ignoring duplicate movie: " + movie_id)
                        db.session.rollback()
                        pass
                count += 1
                if count % 100 == 0:
                    print(count, " movies read")