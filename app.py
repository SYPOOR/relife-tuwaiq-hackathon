import os
import base64
import binascii
import json
import hashlib
import io
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    jsonify,
)

from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from PIL import Image, ImageOps

from google import genai
from google.genai import types


# =========================================================
# CONFIG
# =========================================================

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

STATIC_FOLDER = BASE_DIR / "static"
UPLOAD_FOLDER = STATIC_FOLDER / "uploads"
IMAGES_FOLDER = STATIC_FOLDER / "images"
ASSETS_FOLDER = STATIC_FOLDER / "assets"

DATABASE_PATH = BASE_DIR / "app.db"


# إنشاء المجلدات تلقائياً
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
IMAGES_FOLDER.mkdir(parents=True, exist_ok=True)
ASSETS_FOLDER.mkdir(parents=True, exist_ok=True)


ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "webp",
}

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}


app = Flask(__name__)


app.config["UPLOAD_FOLDER"] = str(
    UPLOAD_FOLDER
)


app.config["MAX_CONTENT_LENGTH"] = (
    10 * 1024 * 1024
)


app.secret_key = os.getenv(
    "SECRET_KEY",
    "eco-prototype-secret",
)


GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY"
)


# =========================================================
# GEMINI CLIENT
# =========================================================

gemini_client = None


if GEMINI_API_KEY:

    gemini_client = genai.Client(
        api_key=GEMINI_API_KEY
    )

else:

    print(
        "⚠ GEMINI_API_KEY غير موجود"
    )


# =========================================================
# DATABASE
# =========================================================

def get_db():

    db = sqlite3.connect(
        DATABASE_PATH
    )

    db.row_factory = sqlite3.Row

    return db


def init_db():

    db = get_db()

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS posts (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            username TEXT NOT NULL,

            avatar TEXT DEFAULT '🌱',

            caption TEXT NOT NULL,

            image TEXT,

            likes INTEGER DEFAULT 0,

            comments INTEGER DEFAULT 0,

            is_seed INTEGER DEFAULT 0,

            created_at TEXT NOT NULL
        )
        """
    )

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS analyses (
            id TEXT PRIMARY KEY,
            source_image TEXT NOT NULL,
            ideas_image TEXT NOT NULL,
            result_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            image_hash TEXT
        )
        """
    )

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS post_likes (
            post_id INTEGER NOT NULL,
            liker_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (post_id, liker_id),
            FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
        )
        """
    )

    analysis_columns = {
        row["name"]
        for row in db.execute("PRAGMA table_info(analyses)").fetchall()
    }
    if "image_hash" not in analysis_columns:
        db.execute("ALTER TABLE analyses ADD COLUMN image_hash TEXT")
    db.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_analyses_image_hash "
        "ON analyses(image_hash) WHERE image_hash IS NOT NULL"
    )

    db.commit()

    db.close()


# =========================================================
# COMMUNITY POSTS
# =========================================================

def seed_community_posts():

    db = get_db()

    exists = db.execute(
        """
        SELECT id
        FROM posts

        WHERE is_seed = 1

        LIMIT 1
        """
    ).fetchone()


    if exists:

        db.close()

        return


    posts = [

        (
            "سارة",
            "👩🏻",
            "حوّلت قارورة مياه قديمة إلى أصيص صغير للنبات 🌱",
            "images/bottle-plant.png",
            28,
            4,
        ),

        (
            "خالد",
            "👨🏻",
            "علبة كانت رايحة للنفايات وصارت منظم للأقلام على مكتبي ✏️",
            "images/pencil-holder.png",
            17,
            2,
        ),

        (
            "نورة",
            "👩🏻‍🦱",
            "مرطبان زجاج قديم تحول إلى مزهرية بسيطة للبيت 🌷",
            "images/glass-vase.png",
            35,
            6,
        ),

        (
            "عبدالله",
            "👨🏻‍🦱",
            "استخدمت كرتون قديم وسويت منه منظم للأغراض الصغيرة 📦",
            "images/cardboard-organizer.png",
            21,
            3,
        ),

        (
            "ريم",
            "👩🏻",
            "بدل ما أرمي العبوة البلاستيكية حولتها إلى وعاء لزراعة النعناع 🌿",
            "images/plastic-planter.png",
            42,
            7,
        ),
    ]


    for post in posts:

        db.execute(
            """
            INSERT INTO posts
            (
                username,
                avatar,
                caption,
                image,
                likes,
                comments,
                is_seed,
                created_at
            )

            VALUES (
                ?, ?, ?, ?, ?, ?, 1, ?
            )
            """,

            (
                post[0],
                post[1],
                post[2],
                post[3],
                post[4],
                post[5],

                datetime.now().isoformat(),
            ),
        )


    db.commit()

    db.close()


# =========================================================
# FILE HELPERS
# =========================================================

def allowed_file(filename):

    return (
        "."
        in filename

        and

        filename
        .rsplit(".", 1)[1]
        .lower()

        in ALLOWED_EXTENSIONS
    )


def has_valid_image_signature(image):
    position = image.stream.tell()
    header = image.stream.read(16)
    image.stream.seek(position)
    return (
        header.startswith(b"\xff\xd8\xff")
        or header.startswith(b"\x89PNG\r\n\x1a\n")
        or (header.startswith(b"RIFF") and header[8:12] == b"WEBP")
    )


def save_uploaded_image(image):

    if not image:

        return None


    if not image.filename:

        return None


    if not allowed_file(
        image.filename
    ):

        return None

    if image.mimetype not in ALLOWED_MIME_TYPES:
        return None

    if not has_valid_image_signature(image):
        return None


    safe_name = secure_filename(
        image.filename
    )


    extension = (
        safe_name
        .rsplit(".", 1)[1]
        .lower()
    )


    filename = (
        f"{uuid.uuid4().hex}.{extension}"
    )


    image_path = (
        UPLOAD_FOLDER
        / filename
    )


    image.save(
        image_path
    )


    return filename


# =========================================================
# STATIC DESIGN ASSET GENERATION
# يولد مرة واحدة فقط
# =========================================================

def generate_design_asset(
    filename,
    prompt,
):

    """
    أصول تصميم ثابتة.

    إذا الملف موجود:
    لا يستدعي Gemini.

    إذا غير موجود:
    يولده مرة واحدة ويحفظه.
    """

    output_path = (
        ASSETS_FOLDER
        / filename
    )


    # الملف موجود
    if (
        output_path.exists()
        and output_path.stat().st_size > 0
    ):

        return True


    if not gemini_client:

        print(
            f"⚠ تعذر إنشاء {filename}: Gemini غير مهيأ"
        )

        return False


    print(
        f"🎨 إنشاء أصل التصميم: {filename}"
    )


    try:

        response = (
            gemini_client
            .models
            .generate_content(

                model=
                "gemini-3.1-flash-image",

                contents=prompt,

                config=
                types.GenerateContentConfig(

                    response_modalities=[
                        "IMAGE"
                    ],

                    image_config=
                        types.ImageConfig(

                            aspect_ratio="1:1"
                        )
                )
            )
        )


        if not response.candidates:

            return False


        for candidate in response.candidates:

            if not candidate.content:

                continue


            for part in (
                candidate
                .content
                .parts
                or []
            ):

                if (
                    part.inline_data
                    and
                    part.inline_data.data
                ):

                    output_path.write_bytes(
                        part.inline_data.data
                    )


                    print(
                        f"✓ تم إنشاء {filename}"
                    )

                    return True


        print(
            f"⚠ لم يتم إرجاع صورة لـ {filename}"
        )

        return False


    except Exception as error:

        print(
            f"⚠ فشل إنشاء {filename}"
        )

        print(error)

        return False


# =========================================================
# GENERATE APP DESIGN ASSETS
# =========================================================

def create_design_assets():

    """
    هذه العناصر ثابتة في التطبيق.
    ستتولد أول مرة فقط.
    """


    # -----------------------------------------------------
    # 1. LOGO
    # -----------------------------------------------------

    generate_design_asset(

        "logo.png",

        """
Create a clean premium mobile application logo
for an Arabic sustainability and circular economy app.

The visual identity should be inspired by:
recycling,
second life,
nature,
circular economy,
reuse.

Create a simple elegant green recycling symbol
integrated subtly with a small leaf.

Minimal flat vector-like design.

Deep natural green and soft sage green.

White or transparent-looking clean background.

Centered icon.

No English text.
No Arabic text.
No letters.
No mockup.
No phone.
No shadows.
No complex details.

Designed to work as a mobile app icon
and small navigation brand mark.

Modern Saudi digital product aesthetic.
"""
    )


    # -----------------------------------------------------
    # 2. WELCOME ILLUSTRATION
    # -----------------------------------------------------

    generate_design_asset(

        "welcome-illustration.png",

        """
Create a premium soft editorial illustration
for a mobile sustainability application.

Scene:

A green recycling bin in the center.

Around it:
small plants,
leaves,
natural stones,
soft green vegetation.

The recycling icon is visible
on the front of the bin.

Style:
modern,
minimal,
warm,
friendly,
high-end mobile application illustration.

Inspired by sustainability,
circular economy,
reuse,
second life.

Cream and warm off-white background.

Muted natural green color palette.

Soft watercolor mixed with
clean modern digital illustration.

Lots of empty breathing space.

No people.
No words.
No Arabic text.
No English text.
No logos except a generic recycling symbol.

Vertical composition suitable
for a mobile onboarding screen.
"""
    )


    # -----------------------------------------------------
    # 3. LEAVES DECORATION
    # -----------------------------------------------------

    generate_design_asset(

        "leaves-bottom.png",

        """
Create a clean decorative botanical illustration
for the bottom edge of a mobile application screen.

A horizontal arrangement
of soft green leaves and small plants.

The vegetation should grow upward
from the bottom edge.

Elegant,
minimal,
airy,
modern sustainability UI style.

Soft sage,
olive,
and natural green colors.

Very light cream background.

No text.
No people.
No objects.
No recycling bins.
No borders.

The upper two thirds of the image
should contain mostly empty space.

Designed as a subtle bottom decoration
behind a loading or analysis screen.
"""
    )


    # -----------------------------------------------------
    # 4. EMPTY COMMUNITY ILLUSTRATION
    # -----------------------------------------------------

    generate_design_asset(

        "empty-community.png",

        """
Create a small friendly illustration
for an empty state in a sustainability community app.

Show two simple recycled handmade plant pots
with small healthy green plants.

One can be created from
a reused plastic bottle.

The second can be created
from a reused household container.

Modern minimal mobile UI illustration.

Soft cream background.

Natural muted green palette.

Friendly,
clean,
premium,
not childish.

No people.
No text.
No letters.
No logos.

Centered composition
with plenty of breathing space.
"""
    )


# =========================================================
# AI ANALYSIS
# =========================================================

class AnalysisError(Exception):
    pass


def prepare_api_image(image_path):
    """Create one compact normalized image shared by both Gemini calls."""
    try:
        with Image.open(image_path) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=82, optimize=True)
            return output.getvalue(), "image/jpeg"
    except Exception as error:
        raise AnalysisError("تعذر تجهيز الصورة للتحليل.") from error

def analyze_with_gemini(
    image_path,
    api_image=None,
):
    if not gemini_client:
        raise AnalysisError("مفتاح GEMINI_API_KEY غير موجود في ملف .env")

    api_bytes, api_mime = api_image or prepare_api_image(image_path)

    prompt = """
حلل الغرض الظاهر فعلياً في الصورة لتطبيق عربي للاستدامة. أعد JSON فقط
بالعربية وفق المخطط. أنت حر تماماً في ابتكار الاقتراحات ولا توجد قائمة أفكار
مسبقة أو نوع مطلوب. اختر أفضل أربع أفكار مناسبة لهذا الغرض تحديداً، ورتبها
من الأكثر منطقية وسهولة وفائدة. يجب أن تكون قابلة للصنع في المنزل بمواد
وأدوات شائعة، قليلة التكلفة، وآمنة قدر الإمكان. تجنب الأفكار المعقدة أو
الزخرفية بلا فائدة. لكل فكرة اكتب وصفاً دقيقاً، مستوى صعوبة، وقتاً تقديرياً،
المواد المطلوبة، مخططاً مختصراً، و4 إلى 7 خطوات تنفيذ واضحة.
لا تفترض أن الغرض قارورة. إذا كانت الصورة غير واضحة اجعل item_name يوضح ذلك.
"""

    schema = {
        "type": "object",
        "properties": {
            "item_name": {"type": "string"},
            "material": {"type": "string"},
            "category": {"type": "string"},
            "recyclable": {"type": "boolean"},
            "recycling_instruction": {"type": "string"},
            "reason": {"type": "string"},
            "ideas": {
                "type": "array",
                "minItems": 4,
                "maxItems": 4,
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "difficulty": {"type": "string", "enum": ["سهل", "متوسط"]},
                        "time_minutes": {"type": "integer", "minimum": 5, "maximum": 120},
                        "materials": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 6,
                            "items": {"type": "string"},
                        },
                        "plan": {"type": "string"},
                        "steps": {
                            "type": "array",
                            "minItems": 4,
                            "maxItems": 7,
                            "items": {"type": "string"},
                        },
                    },
                    "required": [
                        "title", "description", "difficulty", "time_minutes",
                        "materials", "plan", "steps"
                    ],
                },
            },
        },
        "required": [
            "item_name", "material", "category", "recyclable",
            "recycling_instruction", "reason", "ideas",
        ],
    }

    try:
        response = gemini_client.models.generate_content(
            model=os.getenv("GEMINI_TEXT_MODEL", "gemini-3.1-flash-lite"),
            contents=[
                prompt,
                types.Part.from_bytes(
                    data=api_bytes,
                    mime_type=api_mime,
                ),
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=schema,
                temperature=0.2,
            ),
        )
        result = json.loads(response.text)
        emojis = ["🌱", "✏️", "💧", "♻️"]
        for index, idea_item in enumerate(result["ideas"], start=1):
            idea_item["id"] = index
            idea_item["emoji"] = emojis[index - 1]
        return result
    except Exception as error:
        app.logger.warning("تعذر تحليل الصورة عبر Gemini: %s", type(error).__name__)
        raise AnalysisError("تعذر تحليل الصورة بالذكاء الاصطناعي. حاول مجدداً.") from error


def generate_ideas_image(image_path, result, api_image=None):
    api_bytes, api_mime = api_image or prepare_api_image(image_path)
    ideas_text = "\n".join(
        f"Panel {index}: {idea['title']} — {idea['description']}"
        for index, idea in enumerate(result["ideas"], start=1)
    )
    prompt = f"""
Use the uploaded object as the exact source material. Create one square 2x2
four-panel visual showing four realistic finished reuse outcomes. Each panel
must clearly preserve recognizable features/material of the uploaded object.
The panels, in reading order, represent:
{ideas_text}
Modern premium sustainability editorial photography, warm cream background,
soft natural green accents, consistent lighting, clear separators, no people,
no logos, no captions, no letters, no watermark-like decoration. Exactly four
equal panels and one outcome per panel.
"""
    try:
        response = gemini_client.models.generate_content(
            model=os.getenv(
                "GEMINI_IMAGE_MODEL",
                "gemini-3.1-flash-lite-image",
            ),
            contents=[
                types.Part.from_bytes(
                    data=api_bytes,
                    mime_type=api_mime,
                ),
                prompt,
            ],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio="1:1"),
            ),
        )
        for candidate in response.candidates or []:
            if not candidate.content:
                continue
            for part in candidate.content.parts or []:
                if part.inline_data and part.inline_data.data:
                    filename = f"ideas-{uuid.uuid4().hex}.png"
                    (UPLOAD_FOLDER / filename).write_bytes(part.inline_data.data)
                    return filename
    except Exception as error:
        app.logger.warning("تعذر توليد صورة الاقتراحات: %s", type(error).__name__)
        raise AnalysisError("تم التحليل لكن تعذر توليد صورة الاقتراحات. حاول مجدداً.") from error
    raise AnalysisError("لم يُرجع Gemini صورة للاقتراحات. حاول مجدداً.")


def save_camera_image(data_url):
    prefix = "data:image/jpeg;base64,"
    if not data_url or not data_url.startswith(prefix):
        return None
    try:
        raw = base64.b64decode(data_url[len(prefix):], validate=True)
    except (ValueError, binascii.Error):
        return None
    if (
        not raw
        or len(raw) > app.config["MAX_CONTENT_LENGTH"]
        or not raw.startswith(b"\xff\xd8\xff")
    ):
        return None
    filename = f"{uuid.uuid4().hex}.jpg"
    (UPLOAD_FOLDER / filename).write_bytes(raw)
    return filename


# =========================================================
# HOME
# =========================================================

@app.route("/")
def index():
    db = get_db()
    analysis_count = db.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
    community_count = db.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    db.close()

    return render_template(
        "index.html",
        analysis_count=analysis_count,
        community_count=community_count,
        eco_score=analysis_count * 10,
    )


@app.route("/impact")
def impact():
    db = get_db()
    analysis_count = db.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
    post_count = db.execute(
        "SELECT COUNT(*) FROM posts WHERE is_seed = 0"
    ).fetchone()[0]
    received_likes = db.execute(
        "SELECT COALESCE(SUM(likes), 0) FROM posts WHERE is_seed = 0"
    ).fetchone()[0]
    db.close()

    eco_score = analysis_count * 10 + post_count * 5
    ideas_count = analysis_count * 4
    return render_template(
        "impact.html",
        analysis_count=analysis_count,
        ideas_count=ideas_count,
        post_count=post_count,
        received_likes=received_likes,
        eco_score=eco_score,
    )


# =========================================================
# ANALYZE
# =========================================================

@app.route(
    "/analyze",
    methods=["POST"],
)
def analyze():

    image = request.files.get(
        "image"
    )

    camera_image = request.form.get("camera_image", "")


    if (
        (not image or not image.filename)
        and not camera_image
    ):

        return redirect(
            url_for("index")
        )


    if image and image.filename and (
        not allowed_file(image.filename)
        or image.mimetype not in ALLOWED_MIME_TYPES
        or not has_valid_image_signature(image)
    ):

        return jsonify(
            {
                "success":
                    False,

                "message":
                    "صيغة الصورة غير مدعومة",
            }
        ), 400


    filename = (
        save_uploaded_image(image)
        if image and image.filename
        else save_camera_image(camera_image)
    )


    if not filename:

        return jsonify(
            {
                "success":
                    False,

                "message":
                    "تعذر حفظ الصورة",
            }
        ), 500


    image_path = (
        UPLOAD_FOLDER
        / filename
    )

    image_hash = hashlib.sha256(image_path.read_bytes()).hexdigest()
    db = get_db()
    cached = db.execute(
        """
        SELECT id, source_image, ideas_image, result_json
        FROM analyses
        WHERE image_hash = ?
        """,
        (image_hash,),
    ).fetchone()
    db.close()

    if cached:
        if filename != cached["source_image"] and image_path.exists():
            image_path.unlink()
        result = json.loads(cached["result_json"])
        result["ideas_image"] = f"uploads/{cached['ideas_image']}"
        return render_template(
            "result.html",
            result=result,
            image_filename=cached["source_image"],
            analysis_id=cached["id"],
            cache_hit=True,
        )


    try:
        api_image = prepare_api_image(image_path)
        result = analyze_with_gemini(image_path, api_image)
        ideas_filename = generate_ideas_image(image_path, result, api_image)
    except AnalysisError as error:
        return render_template("index.html", error_message=str(error)), 503

    result["ideas_image"] = f"uploads/{ideas_filename}"
    analysis_id = uuid.uuid4().hex

    db = get_db()
    db.execute(
        """
        INSERT INTO analyses
            (id, source_image, ideas_image, result_json, created_at, image_hash)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            analysis_id,
            filename,
            ideas_filename,
            json.dumps(result, ensure_ascii=False),
            datetime.now().isoformat(),
            image_hash,
        ),
    )
    db.commit()
    db.close()


    return render_template(

        "result.html",

        result=result,

        image_filename=filename,

        analysis_id=analysis_id,
    )


# =========================================================
# IDEA
# =========================================================

@app.route(
    "/idea/<int:idea_id>"
)
def idea(
    idea_id
):

    analysis_id = request.args.get("analysis", "").strip()
    if not analysis_id:
        return "افتح الفكرة من صفحة نتيجة تحليل حديثة", 404

    if analysis_id:
        db = get_db()
        analysis = db.execute(
            "SELECT result_json, ideas_image FROM analyses WHERE id = ?",
            (analysis_id,),
        ).fetchone()
        db.close()

        if not analysis:
            return "نتيجة التحليل غير موجودة", 404

        result = json.loads(analysis["result_json"])
        selected_idea = next(
            (item for item in result.get("ideas", []) if item.get("id") == idea_id),
            None,
        )
        if not selected_idea:
            return "الفكرة غير موجودة", 404

        selected_idea["plan_image"] = f"uploads/{analysis['ideas_image']}"
        selected_idea["panel_index"] = idea_id
        return render_template("idea.html", idea=selected_idea)

    ideas = {

        1: {

            "id":
                1,

            "title":
                "أصيص نبات",

            "emoji":
                "🌱",

            "description":
                "حوّل القارورة البلاستيكية إلى أصيص صغير للنباتات.",

            "plan":
                "قارورة ← قص ← فتحات ← تربة ← نبات",

            "plan_image":
                None,

            "steps": [

                "اغسل القارورة جيداً.",

                "حدد مكان القص.",

                "اقطع الجزء العلوي بحذر.",

                "اصنع فتحات صغيرة لتصريف الماء.",

                "أضف التربة.",

                "ضع النبتة داخل الأصيص.",
            ],
        },


        2: {

            "id":
                2,

            "title":
                "منظم أقلام",

            "emoji":
                "✏️",

            "description":
                "حوّل الجزء السفلي من القارورة إلى منظم للمكتب.",

            "plan":
                "قارورة ← قص ← تعديل الحواف ← تزيين ← منظم",

            "plan_image":
                None,

            "steps": [

                "اغسل القارورة.",

                "حدد الارتفاع المناسب.",

                "اقطع الجزء العلوي.",

                "تأكد من نعومة الحواف.",

                "زيّن الجزء الخارجي.",

                "ضع الأقلام بداخله.",
            ],
        },


        3: {

            "id":
                3,

            "title":
                "نظام ري",

            "emoji":
                "💧",

            "description":
                "استخدم القارورة لإنشاء نظام ري بطيء للنبات.",

            "plan":
                "قارورة ← ثقوب ← ماء ← تثبيت ← ري",

            "plan_image":
                None,

            "steps": [

                "نظف القارورة.",

                "اصنع ثقوباً صغيرة في الغطاء.",

                "املأها بالماء.",

                "أغلق الغطاء.",

                "ثبتها بجانب النبات.",
            ],
        },


        4: {

            "id":
                4,

            "title":
                "مغذي طيور",

            "emoji":
                "🐦",

            "description":
                "حوّل القارورة إلى مغذي بسيط للطيور.",

            "plan":
                "قارورة ← فتحات ← حامل ← حبوب ← تعليق",

            "plan_image":
                None,

            "steps": [

                "نظف القارورة.",

                "اصنع فتحات جانبية.",

                "أضف مكاناً لوقوف الطيور.",

                "ضع الحبوب.",

                "علّقها في مكان مناسب.",
            ],
        },
    }


    selected_idea = ideas.get(
        idea_id
    )


    if not selected_idea:

        return (
            "الفكرة غير موجودة",
            404
        )


    return render_template(

        "idea.html",

        idea=selected_idea,
    )


# =========================================================
# COMMUNITY
# =========================================================

@app.route(
    "/community"
)
def community():

    db = get_db()


    posts = db.execute(
        """
        SELECT *
        FROM posts

        ORDER BY id DESC
        """
    ).fetchall()


    db.close()


    return render_template(

        "community.html",

        posts=posts,
    )


# =========================================================
# CREATE POST
# =========================================================

@app.route(
    "/community/post",
    methods=["POST"],
)
def create_post():

    username = request.form.get(
        "username",
        "مستخدم",
    ).strip()


    caption = request.form.get(
        "caption",
        "",
    ).strip()


    image = request.files.get(
        "image"
    )


    if not caption:

        return redirect(
            url_for("community")
        )


    image_path = None


    if (
        image
        and
        image.filename
    ):

        if (
            not allowed_file(image.filename)
            or image.mimetype not in ALLOWED_MIME_TYPES
        ):
            return jsonify({
                "success": False,
                "message": "صيغة الصورة غير مدعومة",
            }), 400

        filename = save_uploaded_image(
            image
        )


        if filename:

            image_path = (
                f"uploads/{filename}"
            )
        else:
            return jsonify({
                "success": False,
                "message": "تعذر حفظ الصورة",
            }), 400


    if not username:

        username = "مستخدم"


    db = get_db()


    db.execute(
        """
        INSERT INTO posts
        (
            username,
            avatar,
            caption,
            image,
            likes,
            comments,
            is_seed,
            created_at
        )

        VALUES (
            ?, ?, ?, ?, 0, 0, 0, ?
        )
        """,

        (
            username,

            "🌱",

            caption,

            image_path,

            datetime.now().isoformat(),
        ),
    )


    db.commit()

    db.close()


    return redirect(
        url_for("community")
    )


# =========================================================
# LIKE
# =========================================================

@app.route(
    "/community/like/<int:post_id>",
    methods=["POST"],
)
def like_post(
    post_id
):

    db = get_db()


    post = db.execute(
        """
        SELECT *
        FROM posts

        WHERE id = ?
        """,

        (
            post_id,
        ),
    ).fetchone()


    if not post:

        db.close()

        return jsonify(
            {
                "success":
                    False,
            }
        ), 404


    payload = request.get_json(silent=True) or {}
    liked = payload.get("liked")
    liker_id = str(payload.get("liker_id", "")).strip()

    if not isinstance(liked, bool) or not liker_id or len(liker_id) > 128:
        db.close()
        return jsonify({
            "success": False,
            "message": "حالة الإعجاب غير صالحة",
        }), 400

    changed = False

    if liked:
        cursor = db.execute(
            """
            INSERT OR IGNORE INTO post_likes (post_id, liker_id, created_at)
            VALUES (?, ?, ?)
            """,
            (post_id, liker_id, datetime.now().isoformat()),
        )
        changed = cursor.rowcount > 0
    else:
        cursor = db.execute(
            "DELETE FROM post_likes WHERE post_id = ? AND liker_id = ?",
            (post_id, liker_id),
        )
        changed = cursor.rowcount > 0

    new_likes = max(
        0,
        post["likes"] + ((1 if liked else -1) if changed else 0),
    )


    db.execute(
        """
        UPDATE posts

        SET likes = ?

        WHERE id = ?
        """,

        (
            new_likes,
            post_id,
        ),
    )


    db.commit()

    db.close()


    return jsonify(
        {
            "success":
                True,

            "likes":
                new_likes,

            "liked":
                liked,
        }
    )


# =========================================================
# HEALTH
# =========================================================

@app.route(
    "/api/health"
)
def health():

    return jsonify(
        {
            "status":
                "ok",

            "gemini":
                bool(
                    GEMINI_API_KEY
                ),
        }
    )


@app.errorhandler(413)
def file_too_large(_error):
    return jsonify({
        "success": False,
        "message": "حجم الصورة أكبر من الحد المسموح (10MB)",
    }), 413


# =========================================================
# STARTUP
# =========================================================

init_db()

seed_community_posts()

# أصول التصميم وصور المجتمع ثابتة ومضمّنة مع المشروع؛ لا تُولّد عند التشغيل.


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    app.run(

        debug=True,

      
    )
