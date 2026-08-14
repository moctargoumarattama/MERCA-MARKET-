import os
from flask import Flask, abort, g, render_template, request, session, url_for
from werkzeug.exceptions import HTTPException
from config import Config
from i18n import (
    DEFAULT_LANGUAGE,
    get_language_options,
    get_locale,
    get_translation_report,
    get_text_direction,
    get_translation_map,
    normalize_language,
    safe_redirect_target,
    plural_suffix,
    translate,
)
from models.database import init_db, close_db

t = translate


def _error_page_data(eyebrow, title, lead, detail, tip_title, tips, primary_label, secondary_label):
    return {
        "eyebrow": eyebrow,
        "title": title,
        "lead": lead,
        "detail": detail,
        "tip_title": tip_title,
        "tips": tips,
        "primary_label": primary_label,
        "secondary_label": secondary_label,
    }


ERROR_PAGE_COPY = {
    "fr": {
        "default": _error_page_data(
            "Erreur",
            "Une erreur imprévue est survenue.",
            "La page n'a pas pu être chargée correctement.",
            "Vous pouvez revenir à l'accueil ou nous contacter si le souci persiste.",
            "Que faire maintenant ?",
            [
                "Retournez à l'accueil.",
                "Réessayez dans quelques instants.",
                "Contactez-nous si besoin.",
            ],
            "Retour à l'accueil",
            "Nous contacter",
        ),
        400: _error_page_data(
            "Erreur 400",
            "Requête invalide.",
            "Le formulaire ou le lien utilisé n'a pas pu être traité.",
            "Cela arrive souvent après un formulaire expiré ou un envoi incomplet.",
            "Que faire maintenant ?",
            [
                "Revenez en arrière puis réessayez.",
                "Rechargez la page avant de renvoyer le formulaire.",
                "Contactez-nous si le problème persiste.",
            ],
            "Réessayer",
            "Retour à l'accueil",
        ),
        401: _error_page_data(
            "Erreur 401",
            "Connexion requise.",
            "Cette partie du site demande une authentification.",
            "Si vous pensez que c'est une erreur, revenez à l'accueil ou contactez-nous.",
            "Que faire maintenant ?",
            [
                "Vérifiez que vous êtes connecté avec le bon compte.",
                "Revenez à l'accueil pour repartir proprement.",
                "Demandez de l'aide si besoin.",
            ],
            "Retour à l'accueil",
            "Nous contacter",
        ),
        403: _error_page_data(
            "Erreur 403",
            "Accès refusé.",
            "Vous n'avez pas les autorisations nécessaires pour ouvrir cette page.",
            "Le compte actuel n'a peut-être pas les droits suffisants.",
            "Que faire maintenant ?",
            [
                "Revenez à l'accueil.",
                "Essayez avec un autre compte si vous en avez un.",
                "Contactez-nous si l'accès devrait être autorisé.",
            ],
            "Retour à l'accueil",
            "Nous contacter",
        ),
        404: _error_page_data(
            "Erreur 404",
            "Page introuvable.",
            "Le lien demandé n'existe pas ou n'est plus disponible.",
            "Le contenu a peut-être été déplacé, renommé ou supprimé.",
            "Que faire maintenant ?",
            [
                "Découvrir les produits disponibles.",
                "Revenir à l'accueil.",
                "Utiliser la recherche depuis la page principale.",
            ],
            "Découvrir le catalogue",
            "Retour à l'accueil",
        ),
        405: _error_page_data(
            "Erreur 405",
            "Méthode non autorisée.",
            "Cette action n'est pas disponible depuis cette page.",
            "Essayez de repasser par le site plutôt que par un lien direct.",
            "Que faire maintenant ?",
            [
                "Revenez en arrière.",
                "Rechargez la page puis réessayez.",
                "Si besoin, repartez de l'accueil.",
            ],
            "Revenir en arrière",
            "Retour à l'accueil",
        ),
        413: _error_page_data(
            "Erreur 413",
            "Fichier trop volumineux.",
            "Le fichier envoyé dépasse la taille autorisée.",
            "Réduisez le poids du fichier puis relancez l'envoi.",
            "Que faire maintenant ?",
            [
                "Compressez l'image ou le document.",
                "Réessayez avec un fichier plus léger.",
                "Revenez à l'accueil si vous avez changé de page.",
            ],
            "Retour au formulaire",
            "Retour à l'accueil",
        ),
        429: _error_page_data(
            "Erreur 429",
            "Trop de requêtes.",
            "Trop d'actions ont été envoyées en peu de temps.",
            "Attendez quelques instants avant de recommencer.",
            "Que faire maintenant ?",
            [
                "Patientez puis réessayez.",
                "Évitez de rafraîchir la page trop vite.",
                "Contactez-nous si le blocage dure.",
            ],
            "Retour à l'accueil",
            "Nous contacter",
        ),
        500: _error_page_data(
            "Erreur 500",
            "Erreur interne du serveur.",
            "Nous rencontrons un souci technique temporaire.",
            "Réessayez dans quelques instants, tout devrait revenir à la normale rapidement.",
            "Que faire maintenant ?",
            [
                "Rechargez la page plus tard.",
                "Retournez à l'accueil pour continuer.",
                "Contactez-nous si le problème persiste.",
            ],
            "Retour à l'accueil",
            "Nous contacter",
        ),
    },
    "ar": {
        "default": _error_page_data(
            "خطأ",
            "حدث خطأ غير متوقع.",
            "تعذر تحميل الصفحة بشكل صحيح.",
            "يمكنك العودة إلى الصفحة الرئيسية أو التواصل معنا إذا استمرت المشكلة.",
            "ماذا يمكنك أن تفعل الآن؟",
            [
                "ارجع إلى الصفحة الرئيسية.",
                "جرّب مرة أخرى لاحقاً.",
                "تواصل معنا إذا لزم الأمر.",
            ],
            "العودة إلى الصفحة الرئيسية",
            "تواصل معنا",
        ),
        400: _error_page_data(
            "خطأ 400",
            "طلب غير صالح.",
            "تعذر معالجة النموذج أو الرابط المستخدم.",
            "قد يحدث هذا بعد انتهاء صلاحية النموذج أو عند الإرسال غير المكتمل.",
            "ماذا يمكنك أن تفعل الآن؟",
            [
                "ارجع للخلف ثم جرّب مرة أخرى.",
                "أعد تحميل الصفحة قبل إعادة الإرسال.",
                "تواصل معنا إذا استمرت المشكلة.",
            ],
            "إعادة المحاولة",
            "العودة إلى الصفحة الرئيسية",
        ),
        401: _error_page_data(
            "خطأ 401",
            "تسجيل الدخول مطلوب.",
            "هذا القسم يحتاج إلى مصادقة.",
            "إذا كنت تعتقد أن هذا خطأ، يمكنك العودة إلى الصفحة الرئيسية أو التواصل معنا.",
            "ماذا يمكنك أن تفعل الآن؟",
            [
                "تأكد من أنك مسجل الدخول بالحساب الصحيح.",
                "ارجع إلى الصفحة الرئيسية.",
                "اطلب المساعدة إذا لزم الأمر.",
            ],
            "العودة إلى الصفحة الرئيسية",
            "تواصل معنا",
        ),
        403: _error_page_data(
            "خطأ 403",
            "الوصول مرفوض.",
            "ليست لديك الصلاحيات اللازمة لعرض هذه الصفحة.",
            "قد لا يملك الحساب الحالي الإذن المطلوب.",
            "ماذا يمكنك أن تفعل الآن؟",
            [
                "ارجع إلى الصفحة الرئيسية.",
                "جرّب بحساب آخر إذا كان متاحاً.",
                "تواصل معنا إذا كان يجب أن يكون الوصول متاحاً.",
            ],
            "العودة إلى الصفحة الرئيسية",
            "تواصل معنا",
        ),
        404: _error_page_data(
            "خطأ 404",
            "الصفحة غير موجودة.",
            "الرابط المطلوب غير متاح أو تم نقله.",
            "قد يكون المحتوى قد تغير أو تم حذفه.",
            "ماذا يمكنك أن تفعل الآن؟",
            [
                "استعرض المنتجات المتاحة.",
                "ارجع إلى الصفحة الرئيسية.",
                "استخدم البحث من الصفحة الرئيسية.",
            ],
            "استعراض الكتالوج",
            "العودة إلى الصفحة الرئيسية",
        ),
        405: _error_page_data(
            "خطأ 405",
            "الطريقة غير مسموحة.",
            "هذا الإجراء لا يمكن تنفيذه من هذه الصفحة.",
            "حاول فتح الصفحة بشكل طبيعي من الموقع.",
            "ماذا يمكنك أن تفعل الآن؟",
            [
                "ارجع للخلف.",
                "أعد تحميل الصفحة ثم جرّب مرة أخرى.",
                "ابدأ من الصفحة الرئيسية إذا لزم الأمر.",
            ],
            "العودة للخلف",
            "العودة إلى الصفحة الرئيسية",
        ),
        413: _error_page_data(
            "خطأ 413",
            "الملف كبير جداً.",
            "الملف المرسل يتجاوز الحجم المسموح به.",
            "قلّص حجم الملف ثم أعد الإرسال.",
            "ماذا يمكنك أن تفعل الآن؟",
            [
                "اضغط الصورة أو المستند.",
                "جرّب ملفاً أصغر.",
                "ارجع إلى الصفحة الرئيسية إذا انتقلت من مكان آخر.",
            ],
            "العودة إلى النموذج",
            "العودة إلى الصفحة الرئيسية",
        ),
        429: _error_page_data(
            "خطأ 429",
            "طلبات كثيرة جداً.",
            "تم إرسال الكثير من الطلبات خلال وقت قصير.",
            "انتظر قليلاً قبل المحاولة من جديد.",
            "ماذا يمكنك أن تفعل الآن؟",
            [
                "انتظر ثم حاول مرة أخرى.",
                "لا تُعد تحميل الصفحة بسرعة كبيرة.",
                "تواصل معنا إذا استمر الحظر.",
            ],
            "العودة إلى الصفحة الرئيسية",
            "تواصل معنا",
        ),
        500: _error_page_data(
            "خطأ 500",
            "حدث خطأ داخلي في الخادم.",
            "نواجه مشكلة تقنية مؤقتة.",
            "يمكنك المحاولة لاحقاً أو التواصل معنا إذا استمرت المشكلة.",
            "ماذا يمكنك أن تفعل الآن؟",
            [
                "أعد تحميل الصفحة لاحقاً.",
                "ارجع إلى الصفحة الرئيسية للمتابعة.",
                "تواصل معنا إذا لم تُحل المشكلة.",
            ],
            "العودة إلى الصفحة الرئيسية",
            "تواصل معنا",
        ),
    },
}


def get_error_page_content(language: str, code: int) -> dict:
    language_copy = ERROR_PAGE_COPY.get(language, ERROR_PAGE_COPY[DEFAULT_LANGUAGE])
    return language_copy.get(code, language_copy["default"])


def generate_csrf_token():
    if "_csrf_token" not in session:
        session["_csrf_token"] = os.urandom(32).hex()
    return session["_csrf_token"]


def validate_csrf_token(token: str | None) -> bool:
    return token and session.get("_csrf_token") and token == session.get("_csrf_token")


def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(Config)
    # Keep the styled error pages active even when the app is launched in debug.
    app.config["PROPAGATE_EXCEPTIONS"] = False
    app.add_template_global(generate_csrf_token, "csrf_token")

    app.teardown_appcontext(close_db)

    from routes.public import public_bp
    from routes.admin import admin_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    @app.before_request
    def ensure_language():
        current_language = session.get("ui_lang")

        if current_language not in get_language_options():
            preferred = request.accept_languages.best_match(tuple(get_language_options().keys()))
            session["ui_lang"] = normalize_language(preferred or DEFAULT_LANGUAGE)
        else:
            session["ui_lang"] = normalize_language(current_language)

    @app.before_request
    def validate_csrf():
        if request.method == "POST":
            token = request.form.get("_csrf_token")
            if not validate_csrf_token(token):
                abort(400, description="Invalid CSRF token")

    @app.context_processor
    def inject_settings():
        current_language = get_locale()
        translation_report = get_translation_report()
        return {
            "shop_name": app.config["SHOP_NAME"],
            "shop_address": app.config["SHOP_ADDRESS"],
            "whatsapp_number": app.config["WHATSAPP_NUMBER"],
            "facebook_url": app.config["FACEBOOK_URL"],
            "instagram_url": app.config["INSTAGRAM_URL"],
            "current_lang": current_language,
            "text_direction": get_text_direction(current_language),
            "languages": get_language_options(),
            "ui_strings": get_translation_map(current_language),
            "default_ui_strings": get_translation_map(DEFAULT_LANGUAGE),
            "translation_missing_keys": translation_report.get(current_language, {}).get("missing", []),
            "asset_version": app.config["ASSET_VERSION"],
            "plural_suffix": plural_suffix,
            "t": translate,
            "csrf_token": generate_csrf_token,
        }

    def build_error_page_context(code: int):
        current_language = get_locale()
        content = dict(get_error_page_content(current_language, code))
        home_url = url_for("public.index")
        products_url = url_for("public.index", _anchor="products")
        back_url = safe_redirect_target(request.referrer, home_url)
        whatsapp_url = f"https://wa.me/{app.config['WHATSAPP_NUMBER']}"
        contact_label = "Contact"
        try:
            contact_label = translate("common.contact")
        except Exception:
            app.logger.exception("Failed to translate error page contact label")

        if code == 404:
            primary_url = products_url
            primary_label = content["primary_label"]
            secondary_url = home_url
            secondary_label = content["secondary_label"]
        elif code in {400, 405, 413}:
            if back_url == home_url:
                primary_url = home_url
                primary_label = content["secondary_label"]
                secondary_url = whatsapp_url
                secondary_label = contact_label
            else:
                primary_url = back_url
                primary_label = content["primary_label"]
                secondary_url = home_url
                secondary_label = content["secondary_label"]
        else:
            primary_url = home_url
            primary_label = content["primary_label"]
            secondary_url = whatsapp_url
            secondary_label = contact_label

        content.update(
            {
                "code": code,
                "primary_label": primary_label,
                "primary_url": primary_url,
                "secondary_label": secondary_label,
                "secondary_url": secondary_url,
                "home_url": home_url,
                "products_url": products_url,
                "back_url": back_url,
                "whatsapp_url": whatsapp_url,
            }
        )
        return content

    def safe_build_error_page_context(code: int):
        try:
            return build_error_page_context(code)
        except Exception:
            app.logger.exception("Failed to build error page context for code %s", code)
            return {
                "code": code,
                "eyebrow": "Erreur" if code != 500 else "Erreur interne",
                "title": "Une erreur est survenue.",
                "lead": "Le serveur n'a pas pu traiter la requête.",
                "detail": "Veuillez réessayer ou contacter le support si le problème persiste.",
                "tip_title": "Que faire maintenant ?",
                "tips": [
                    "Retournez à l'accueil.",
                    "Réessayez plus tard.",
                    "Contactez-nous si besoin.",
                ],
                "primary_label": "Accueil",
                "primary_url": url_for("public.index"),
                "secondary_label": "Contact",
                "secondary_url": f"https://wa.me/{app.config['WHATSAPP_NUMBER']}",
                "home_url": url_for("public.index"),
                "products_url": url_for("public.index", _anchor="products"),
                "back_url": safe_redirect_target(request.referrer, url_for("public.index")),
                "whatsapp_url": f"https://wa.me/{app.config['WHATSAPP_NUMBER']}",
            }

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        code = error.code or 500
        page = safe_build_error_page_context(code)
        response = error.get_response()
        response.data = render_template("error.html", error=page)
        response.content_type = "text/html; charset=utf-8"
        return response

    @app.errorhandler(Exception)
    def handle_unexpected_exception(error):
        app.logger.exception("Unhandled exception while processing %s", request.path)
        page = safe_build_error_page_context(500)
        return render_template("error.html", error=page), 500

    @app.after_request
    def set_security_headers(response):
        # Content Security Policy: permissive for dev but restricts basics
        csp = (
            "default-src 'self'; "
            "img-src 'self' data: https:; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https:; "
            "style-src 'self' 'unsafe-inline' https:; "
            "font-src 'self' data:;"
        )
        response.headers.setdefault('Content-Security-Policy', csp)
        if app.config.get("SESSION_COOKIE_SECURE"):
            response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
        response.headers.setdefault('X-Frame-Options', 'DENY')
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.headers.setdefault('Permissions-Policy', 'geolocation=(), microphone=()')
        return response

    @app.cli.command("init-db")
    def init_db_command():
        init_db()
        print("Database initialized.")

    @app.cli.command("check-i18n")
    def check_i18n_command():
        report = get_translation_report()

        if not report:
            print("Translation coverage OK.")
            return

        print("Translation coverage issues detected:")
        for language, info in report.items():
            missing = info.get("missing", [])
            extra = info.get("extra", [])
            if missing:
                print(f"- {language} missing: {', '.join(missing)}")
            if extra:
                print(f"- {language} extra: {', '.join(extra)}")

        raise SystemExit(1)

    with app.app_context():
        init_db()

    return app


app = create_app()

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=debug)
