from flask import Flask, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///qlsach.db"
app.config["SECRET_KEY"] = "dev"
db.init_app(app)


# ======================== MODEL ========================

class Category(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str] = mapped_column(String(300), default="")
    books: Mapped[list["Book"]] = db.relationship(back_populates="category", cascade="all, delete-orphan")


class Book(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    author: Mapped[str] = mapped_column(String(100))
    year: Mapped[int] = mapped_column(default=0)
    category_id: Mapped[int] = mapped_column(db.ForeignKey("category.id"))
    category: Mapped["Category"] = db.relationship(back_populates="books")


with app.app_context():
    db.create_all()
    if not db.session.execute(db.select(Category)).scalar():
        c1 = Category(name="Văn học", description="Tiểu thuyết, truyện ngắn, thơ")
        c2 = Category(name="Khoa học", description="Vật lý, hóa học, sinh học")
        c3 = Category(name="Công nghệ", description="Lập trình, mạng, AI")
        db.session.add_all([c1, c2, c3])
        db.session.flush()
        db.session.add_all([
            Book(title="Dế Mèn phiêu lưu ký", author="Tô Hoài", year=1941, category_id=c1.id),
            Book(title="Số đỏ", author="Vũ Trọng Phụng", year=1936, category_id=c1.id),
            Book(title="Lược sử thời gian", author="Stephen Hawking", year=1988, category_id=c2.id),
            Book(title="Cosmos", author="Carl Sagan", year=1980, category_id=c2.id),
            Book(title="Flask Web Development", author="Miguel Grinberg", year=2018, category_id=c3.id),
            Book(title="Clean Code", author="Robert C. Martin", year=2008, category_id=c3.id),
        ])
        db.session.commit()



# ======================== DASHBOARD ========================

@app.route("/")
def dashboard():
    cats = db.session.execute(db.select(Category).order_by(Category.name)).scalars().all()
    total_books = db.session.execute(db.select(db.func.count(Book.id))).scalar()
    total_cats = len(cats)
    return render_template("dashboard.html", cats=cats, total_books=total_books, total_cats=total_cats)


# ======================== CRUD DANH MỤC ========================

@app.route("/categories")
def category_list():
    cats = db.session.execute(db.select(Category).order_by(Category.name)).scalars().all()
    return render_template("categories.html", cats=cats)


@app.route("/categories/add", methods=["GET", "POST"])
def category_add():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        desc = request.form.get("description", "").strip()
        if not name:
            return render_template("category_form.html", error="Tên danh mục không được trống.", cat=None)
        exists = db.session.execute(db.select(Category).where(Category.name == name)).scalar()
        if exists:
            return render_template("category_form.html", error=f"Danh mục '{name}' đã tồn tại.", cat=None)
        db.session.add(Category(name=name, description=desc))
        db.session.commit()
        return redirect(url_for("category_list"))
    return render_template("category_form.html", cat=None, error=None)


@app.route("/categories/<int:id>/edit", methods=["GET", "POST"])
def category_edit(id):
    cat = db.session.get(Category, id)
    if not cat:
        return "Không tìm thấy danh mục.", 404
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        desc = request.form.get("description", "").strip()
        if not name:
            return render_template("category_form.html", error="Tên danh mục không được trống.", cat=cat)
        dup = db.session.execute(db.select(Category).where(Category.name == name, Category.id != id)).scalar()
        if dup:
            return render_template("category_form.html", error=f"Danh mục '{name}' đã tồn tại.", cat=cat)
        cat.name = name
        cat.description = desc
        db.session.commit()
        return redirect(url_for("category_list"))
    return render_template("category_form.html", cat=cat, error=None)


@app.route("/categories/<int:id>/delete", methods=["POST"])
def category_delete(id):
    cat = db.session.get(Category, id)
    if cat:
        db.session.delete(cat)
        db.session.commit()
    return redirect(url_for("category_list"))


# ======================== CRUD SÁCH ========================

@app.route("/categories/<int:cat_id>/books")
def book_list(cat_id):
    cat = db.session.get(Category, cat_id)
    if not cat:
        return "Không tìm thấy danh mục.", 404
    return render_template("books.html", cat=cat)


@app.route("/categories/<int:cat_id>/books/add", methods=["GET", "POST"])
def book_add(cat_id):
    cat = db.session.get(Category, cat_id)
    if not cat:
        return "Không tìm thấy danh mục.", 404
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        year = request.form.get("year", "").strip()
        if not title or not author:
            return render_template("book_form.html", cat=cat, book=None, error="Tên sách và tác giả không được trống.")
        try:
            y = int(year) if year else 0
        except ValueError:
            return render_template("book_form.html", cat=cat, book=None, error="Năm phải là số.")
        db.session.add(Book(title=title, author=author, year=y, category_id=cat.id))
        db.session.commit()
        return redirect(url_for("book_list", cat_id=cat.id))
    return render_template("book_form.html", cat=cat, book=None, error=None)


@app.route("/books/<int:id>/edit", methods=["GET", "POST"])
def book_edit(id):
    book = db.session.get(Book, id)
    if not book:
        return "Không tìm thấy sách.", 404
    cats = db.session.execute(db.select(Category).order_by(Category.name)).scalars().all()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        year = request.form.get("year", "").strip()
        new_cat = request.form.get("category_id", "").strip()
        if not title or not author:
            return render_template("book_form.html", cat=book.category, book=book, error="Tên sách và tác giả không được trống.", cats=cats)
        try:
            y = int(year) if year else 0
        except ValueError:
            return render_template("book_form.html", cat=book.category, book=book, error="Năm phải là số.", cats=cats)
        book.title = title
        book.author = author
        book.year = y
        if new_cat:
            book.category_id = int(new_cat)
        db.session.commit()
        return redirect(url_for("book_list", cat_id=book.category_id))
    return render_template("book_form.html", cat=book.category, book=book, error=None, cats=cats)


@app.route("/books/<int:id>/delete", methods=["POST"])
def book_delete(id):
    book = db.session.get(Book, id)
    if book:
        cat_id = book.category_id
        db.session.delete(book)
        db.session.commit()
        return redirect(url_for("book_list", cat_id=cat_id))
    return redirect(url_for("dashboard"))



if __name__ == "__main__":
    app.run(debug=True)
