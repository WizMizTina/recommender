# AI and the Web
@Authors: Clive Tinashe Marimo

## About

This is a recommender tool that recommends movies based on user rating and finding nearest users to current user based on the rated movies and genres selected. The user is then recommended unseen movies from most similar fellow users who rated certain movies that the current user has not seen favourably. Cosine similarity, nearest neighbours and collaborative filtering algorithms are used to find most similar users to current user. Data is stored in a database for easy access and manipulation.


## Dependencies
1. requests
2. scikit-learn
3. flask
4. pandas
5. flask-sqlalchemy


## Running the Flask Search Engine:
1. Install dependencies with **pip install -r requirements.txt**.
2. Run the search engine by executing: **flask --app recommender.py run**


## Resources Used:
1. BeautifulSoup Documentation
2. W3C Schools Guides
