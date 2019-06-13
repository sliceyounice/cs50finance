import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/", methods=["GET"])
@login_required
def index():
    """Show portfolio of stocks"""
    stocks = db.execute(
        "SELECT symbol, SUM(shares) FROM transactions WHERE user_id = :id GROUP BY symbol HAVING SUM(shares) > 0",
        id=session['user_id'])
    portfolio = []
    cash = db.execute("SELECT cash from users WHERE id = :id", id=session['user_id'])[0]['cash']
    networth = 0
    if stocks:
        for stock in stocks:
            realtime_stock = lookup(stock['symbol'])
            realtime_stock['shares'] = stock['SUM(shares)']
            realtime_stock['total'] = stock['SUM(shares)'] * realtime_stock['price']
            portfolio.append(realtime_stock)
            networth += realtime_stock['total']
    networth += cash

    return render_template("portfolio.html", portfolio=portfolio, cash=cash, networth=networth)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("buy.html")

    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")

        if not symbol:
            return apology("give me a symbol", 400)

        elif not shares or int(shares) <= 0:
            return apology("positive shares please", 400)

        else:
            stock = lookup(symbol)

            if not stock or stock["name"] == "N/A":
                return apology("wrong symbol", 400)

            cash = db.execute("SELECT cash FROM users WHERE id = :id", id=session["user_id"])[0]["cash"] - int(shares) * stock["price"]

            if cash < 0:
                return apology("not enough money", 400)

            db.execute("UPDATE users SET cash=:cash WHERE id=:id", cash=cash, id=session["user_id"])
            db.execute(
                "INSERT INTO transactions (user_id, symbol, shares, price) VALUES (:user_id, :symbol, :shares, :price)",
                user_id=session["user_id"], symbol=stock["symbol"], shares=int(shares), price=stock["price"])
            return redirect("/")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    return apology("TODO")


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
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

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
    if request.method == "GET":
        return render_template("quote.html")
    if request.method == "POST":
        quoted = lookup(request.form.get("symbol"))
        if quoted:
            return render_template("quoted.html", quoted=quoted)
        else:
            return apology("wrong symbol", 400)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        if not username:
            return apology("must provide username", 400)
        elif not password:
            return apology("must provide password", 400)
        elif password != confirm_password:
            return apology("passwords doesnt match", 400)
        elif db.execute("SELECT COUNT(*) FROM users WHERE username = :username;", username=username)[0]['COUNT(*)'] > 0:
            return apology("such user already exists", 400)
        else:
            session['user_id'] = db.execute("INSERT INTO users (username,hash) VALUES (:username, :hash);",
                                            username=username, hash=generate_password_hash(password))
            flash("Registered!")
            return redirect("/")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "GET":
        stocks = db.execute(
            "SELECT symbol FROM transactions WHERE user_id = :id GROUP BY symbol HAVING SUM(shares) > 0",
            id=session['user_id'])
        return render_template("sell.html", stocks=stocks)
    if request.method == "POST":
        request_symbol = request.form.get("symbol")
        request_shares = request.form.get("shares", type=int)
        if not request_symbol:
            return apology("Missing symbol", 400)

        if not request_shares or request_shares <= 0:
            return apology("Missing shares", 400)

        if request_shares > 0 and request_symbol:
            db_shares = db.execute("SELECT SUM(shares) from transactions WHERE user_id = :id "
                                   "AND symbol = :symbol", symbol=request_symbol, id=session['user_id'])[0][
                'SUM(shares)']
            if not db_shares:
                return apology("wrong symbol", 400)
            if db_shares >= request_shares:
                stock = lookup(request_symbol)
                db.execute("UPDATE users SET cash=(SELECT cash FROM users WHERE id = :user_id)+:cash WHERE id=:user_id",
                           user_id=session['user_id'],
                           cash=stock['price'] * request_shares)
                db.execute("INSERT INTO transactions (user_id, symbol, shares, price) VALUES (:user_id, :symbol,"
                           " :shares, :price)", user_id=session["user_id"], symbol=stock["symbol"],
                           shares=-request_shares, price=stock["price"])
                flash("Sold!")
                return redirect("/")
            else:
                return apology("Too many shares", 400)


def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
