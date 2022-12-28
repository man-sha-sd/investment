import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
import datetime
from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    user_id = session["user_id"]
    transactions_db = db.execute(
        "SELECT symbol, sum(shares) as shares, price from transactions where user_id = ? GROUP BY symbol", user_id)
    cash_db = db.execute("SELECT cash FROM users where id =? ", user_id)
    cash_balance = cash_db[0]["cash"]
    sub_total =0
    for row in transactions_db:
        quote = lookup(row["symbol"])
        row["name"] = quote["name"]
        present_value = row["shares"] * quote["price"]
        row["nav"] = present_value
        sub_total = sub_total + present_value


    return render_template("index.html", database=transactions_db, sub_total = sub_total, cash=cash_balance)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":

        symbol = request.form.get("symbol")

        # check if no shares is numeric or not

        shares_user = request.form.get("shares")
        if not shares_user.isnumeric():
            return apology("minimum ticker is 1", 400)

        shares = int(request.form.get("shares"))

        # prompt if user has not provided symbol

        if not request.form.get("symbol"):
            return apology("Please provide symbol", 403)

        # prompt if user has not provied no of shares
        if not request.form.get("shares"):
            return apology("Please provide no of shares", 403)

        quote = lookup(symbol)

        """ Check if symbol is correct"""
        if quote == None:
            return apology("please check the symbol", 400)

        transaction_value = shares*quote['price']

        user_id = session["user_id"]
        user_cash_db = db.execute(
            "SELECT cash FROM USERS WHERE id = :id", id=user_id)
        user_cash = user_cash_db[0]['cash']

        if transaction_value > user_cash:
            return apology("Not Enough Cash")

        updated_cash = user_cash - transaction_value

        # update cash value post transaction

        db.execute("UPDATE users SET cash = ? WHERE id = ?",
                   updated_cash, user_id)

        # update date of transaction in the transaction table

        date = datetime.datetime.now()

        db.execute("INSERT INTO  transactions (user_id, symbol, shares, price,date) VALUES (?,?,?,?,?) ",
                   user_id, quote["symbol"], shares, quote["price"], date)

        flash("Bought")
        return redirect("/")

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():

    user_id = session["user_id"]
    """Show history of transactions"""
    database = db.execute(
        "SELECT symbol,shares,price,date FROM transactions WHERE user_id =? ", user_id)

    return render_template("/history.html", database=database)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or  check_password_hash(rows[0]["hash"] , request.form.get("password")):
            return apology("invalid username and/or password", 400)


        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    if request.method == "POST":

        symbol = request.form.get("symbol")
        quote = lookup(symbol)

        """ Check if symbol is correct"""
        if quote == None:
            return apology("please check the symbol", 400)


        name = quote['name']
        price = quote['price']

        if not symbol:
            return apology("please provide symbol", 400)

        return render_template("quoted.html", name=name, price=price, symbol=symbol)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    username = request.form.get("username")
    password = request.form.get("password")
    confirmation = request.form.get("confirmation")
    hash = generate_password_hash("password")

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Ensure  password is matching
        elif password != confirmation:
            return apology("passwords not matching ", 400)

        # Query database if username exists
        rows = db.execute("SELECT * from users where username = ?", username)

        if len(rows) != 0:
            return apology("user name not available", 400)

        # insert new user
        db.execute("INSERT INTO users (username, hash) VALUES (?,?)", username, hash)

        return redirect("/")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    user_id = session["user_id"]

    if request.method == "GET":
        symbols_user = db.execute(
            "SELECT symbol FROM transactions WHERE user_id = ? GROUP BY symbol HAVING SUM(shares) > 0", user_id)
        return render_template("sell.html", symbols=[row["symbol"] for row in symbols_user])

    if request.method == "POST":

        if not request.form.get("symbol"):
            return apology("Provide a symbol", 403)

        if not request.form.get("shares"):
            return apology("Submit no of Shares", 403)

    symbol = request.form.get("symbol")
    shares = int(request.form.get("shares"))

    quote = lookup(symbol)

    """ Check if symbol is correct"""
    if quote == None:
        return apology("please check the symbol", 400)

    price = quote['price']

    """Access  the key value pai of the symbol and shares owned by  in the transaction table  """

    shares_owned_db = db.execute(
        "SELECT SUM(shares) AS shares FROM transactions WHERE  user_id = ? AND symbol = ? ", user_id, symbol)

    """ accces the no of shares of value with shares as key """

    shares_owned = shares_owned_db[0]["shares"]

    if shares_owned < shares:
        return apology("Not Enough Shares", 400)

    user_id = session["user_id"]

    transaction_value = shares*price

    user_cash_db = db.execute(
        "SELECT cash FROM users WHERE id = ?", user_id)

    user_cash = user_cash_db[0]["cash"]

    updated_cash = user_cash + transaction_value

    # update cash in data base
    db.execute("UPDATE users SET cash = ? WHERE id = ?", updated_cash, user_id)

    # update date in to the transaction table
    date = datetime.datetime.now()

    db.execute(
        "INSERT INTO transactions (user_id,symbol,shares,price, date ) VALUES  (?,?,?,?,?)", user_id, symbol, -1*shares, quote["price"], date)

    flash("Sold")
    return redirect("/")
