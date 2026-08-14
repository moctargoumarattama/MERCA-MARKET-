from __future__ import annotations

from urllib.parse import urlparse

from flask import has_request_context, request, session

DEFAULT_LANGUAGE = "fr"
SUPPORTED_LANGUAGES = {
    "fr": {
        "code": "fr",
        "label": "FR",
        "name": "Français",
        "dir": "ltr",
    },
    "ar": {
        "code": "ar",
        "label": "AR",
        "name": "العربية",
        "dir": "rtl",
    },
}


TRANSLATIONS = {
    "fr": {
        # Common
        "common.home": "Accueil",
        "common.back_home": "Retour à l'accueil",
        "common.back_catalogue": "Retour au catalogue",
        "common.save": "Enregistrer",
        "common.save_changes": "Enregistrer les modifications",
        "common.modify": "Modifier",
        "common.delete": "Supprimer",
        "common.cancel": "Annuler",
        "common.confirm": "Confirmer",
        "common.more": "Voir plus",
        "common.add": "Ajouter",
        "common.remove": "Retirer",
        "common.loading": "Chargement...",
        "common.search": "Recherche",
        "common.clear": "Effacer",
        "common.language": "Langue",
        "common.contact": "Nous contacter",
        "common.out_of_stock": "Rupture",
        "common.in_stock": "en stock",
        "common.without_category": "Sans categorie",
        "common.visible": "Visible",
        "common.hidden": "Masque",
        "common.available": "Disponible",
        "common.unavailable": "Indisponible",
        "common.quantity": "Quantite",
        "common.total": "Total",
        "common.unit": "unite",
        "common.address": "Adresse",
        "common.follow_us": "Suivez-nous",
        "common.categories": "Categories",
        "common.products": "Produits",
        "common.product": "Produit",

        # Public app
        "app.meta_description": "fruits secs et commande rapide sur WhatsApp.",
        "brand.tagline": "Commande rapide et service direct",
        "brand.logo_alt": "Logo de {shop_name}",
        "nav.cart": "Panier",
        "nav.open_menu": "Ouvrir le menu",
        "nav.close_menu": "Fermer le menu",
        "pwa.install": "Installer l'application",
        "nav.open_admin_menu": "Ouvrir le menu administrateur",
        "footer.quick_order": "Commande rapide",
        "footer.write_whatsapp": "Ecris-nous sur WhatsApp pour commander en quelques secondes.",
        "footer.whatsapp_button": "Commander sur WhatsApp",
        "footer.reply_note": "Reponse directe et commande simplifiee.",
        "footer.address_label": "Adresse",
        "footer.follow_label": "Suivez-nous",
        "footer.facebook": "Facebook",
        "footer.instagram": "Instagram",
        "modal.see_more": "Voir plus",
        "modal.product": "Produit",
        "modal.close": "Fermer",
        "modal.no_description": "Aucune description disponible.",
        "home.page_title": "Accueil",
        "home.hero.title": "Une selection variee, commandee en quelques secondes.",
        "home.hero.subtitle": "Decouvrez nos produits et commandez rapidement sur WhatsApp.",
        "home.hero.cta.products": "Voir les produits",
        "home.hero.cta.whatsapp": "WhatsApp",
        "home.search.placeholder": "Rechercher un produit ou une categorie",
        "home.search.aria": "Recherche instantanee",
        "home.categories.eyebrow": "Nos categories",
        "home.categories.title": "Choisissez votre rayon",
        "home.categories.active": "Categorie active",
        "home.categories.view_products": "Voir les produits",
        "home.categories.empty.title": "Aucune categorie",
        "home.categories.empty.body": "Ajoutez vos rayons depuis l'administration pour commencer la vitrine.",
        "home.filter.eyebrow": "Filtre actif",
        "home.filter.category_prefix": "Categorie",
        "home.filter.search_prefix": "Recherche",
        "home.filter.results": "{count} produit{suffix} trouve{suffix}",
        "home.filter.back": "Retour a l'accueil",
        "home.filter.category_selected": "Categorie selectionnee",
        "home.results.by_category": "Produits de la categorie",
        "home.results.by_search": "Resultats de recherche",
        "home.results.subtitle.category": "{count} produit{suffix} dans ce rayon.",
        "home.results.subtitle.search": "{count} produit{suffix} trouve{suffix}.",
        "home.products.empty.title": "Aucun produit trouve",
        "home.products.empty.by_category": "Aucun produit n'est disponible dans cette categorie pour le moment.",
        "home.products.empty.by_search": "Aucun resultat ne correspond a votre recherche.",
        "home.products.back": "Retour a l'accueil",
        "home.product.no_description": "Aucune description disponible.",
        "home.product.see_more": "Voir plus",
        "home.product.add": "Ajouter au panier",
        "home.product.out_of_stock": "Rupture",
        "home.product.category_empty": "Sans categorie",

        # Cart page
        "cart.page_title": "Panier",
        "cart.kicker": "Panier",
        "cart.title": "Votre commande en cours",
        "cart.subtitle": "Ajustez vos quantites, verifiez le total, puis envoyez le tout sur WhatsApp.",
        "cart.continue": "Continuer vos achats",
        "cart.total_label": "Total",
        "cart.order_note": "Le message sera genere automatiquement avec le detail de chaque produit.",
        "cart.name_label": "Nom du client",
        "cart.name_placeholder": "Votre nom",
        "cart.address_label": "Adresse ou quartier",
        "cart.address_placeholder": "Adresse de livraison ou retrait",
        "cart.whatsapp": "Commander sur WhatsApp",
        "cart.clear": "Vider le panier",
        "cart.empty.title": "Votre panier est vide",
        "cart.empty.body": "Ajoutez des produits depuis le catalogue pour construire votre commande.",
        "cart.empty.button": "Explorer le catalogue",
        "cart.item.unit": "unite",
        "cart.item.stock_available": "{count} dispo",
        "cart.item.stock_out": "Rupture",
        "cart.item.remove": "Supprimer",
        "cart.confirm_clear": "Vider le panier ?",
        "cart.message.intro": "Bonjour {shop_name}, je souhaite passer cette commande :",
        "cart.message.total": "Total : {total}",
        "cart.message.name": "Nom : {name}",
        "cart.message.address": "Adresse : {address}",
        "cart.message.confirm": "Merci de confirmer ma commande.",
        "js.cart.checkout_unavailable": "La commande n'a pas pu etre verifiee. Reessayez dans un instant.",

        # Search/live UI
        "search.loading": "Recherche en cours...",
        "search.unavailable": "La recherche est temporairement indisponible.",
        "search.no_results": "Aucun resultat pour {query}. Essayez un autre mot-cle.",
        "search.categories": "Categories",
        "search.products": "Produits",
        "search.product_stock": "{count} en stock",

        # Quick return
        "quick_return.kicker": "Retour rapide",
        "quick_return.products": "Produits",
        "quick_return.search": "Recherche",

        # Admin
        "admin.space": "Espace administrateur",
        "admin.open_menu": "Ouvrir le menu administrateur",
        "admin.logout": "Deconnexion",
        "admin.menu.overview": "Vue rapide",
        "admin.menu.catalogue": "Catalogue",
        "admin.menu.add_category": "Ajouter une categorie",
        "admin.menu.admins": "Admins",
        "admin.menu.products": "Produits du rayon",
        "admin.menu.add_product": "Ajouter un produit",
        "admin.admins.kicker": "Administrateurs",
        "admin.admins.title": "Creer un second administrateur",
        "admin.admins.subtitle": "Ajoute un autre compte admin pour partager la gestion du site.",
        "admin.admins.primary_label": "Compte principal",
        "admin.admins.secondary_label": "Compte secondaire",
        "admin.admins.username": "Nom d'utilisateur",
        "admin.admins.password": "Mot de passe",
        "admin.admins.new_password": "Nouveau mot de passe (optionnel)",
        "admin.admins.submit": "Creer l'admin",
        "admin.admins.update": "Modifier",
        "admin.admins.delete": "Supprimer",
        "admin.admins.confirm_delete": "Supprimer ce compte administrateur ?",
        "admin.admins.empty.title": "Aucun second administrateur",
        "admin.admins.empty.body": "Tu peux ajouter un autre compte depuis ce formulaire.",
        "admin.login.title": "Administration",
        "admin.login.subtitle": "Connectez-vous pour gerer le catalogue, les categories et les produits.",
        "admin.login.username": "Nom d'utilisateur",
        "admin.login.password": "Mot de passe",
        "admin.login.submit": "Se connecter",
        "admin.login.back": "Retour au site",
        "admin.overview.kicker": "Vue rapide",
        "admin.overview.title": "Accueil admin",
        "admin.overview.subtitle": "Un apercu rapide, puis tu ouvres seulement ce qu'il faut.",
        "admin.stats.categories": "Categories",
        "admin.stats.products": "Produits",
        "admin.stats.visible": "Visibles",
        "admin.stats.sold_out": "Ruptures",
        "admin.stats.today_visits": "Visites aujourd'hui",
        "admin.visits.kicker": "Visites",
        "admin.visits.title": "Nombre de visiteurs par jour",
        "admin.visits.subtitle": "Suivi des visites recentes du site.",
        "admin.visits.empty.title": "Aucune visite",
        "admin.visits.empty.body": "Les statistiques apparaissent ici des que le site recoit des visiteurs.",
        "admin.quick_catalogue": "Catalogue",
        "admin.quick_catalogue_sub": "Voir les categories",
        "admin.quick_add_category": "Ajouter categorie",
        "admin.quick_add_category_sub": "Creer un rayon",
        "admin.quick_products": "Produits",
        "admin.quick_products_sub": "Ouvrir un rayon",
        "admin.quick_add_product": "Ajouter produit",
        "admin.quick_add_product_sub": "Creer un article",
        "admin.catalogue.kicker": "Catalogue",
        "admin.catalogue.title": "Les categories",
        "admin.catalogue.subtitle": "Clique sur une categorie pour voir uniquement ses produits.",
        "admin.catalogue.add_category": "Ajouter une categorie",
        "admin.catalogue.modify": "Modifier",
        "admin.catalogue.delete": "Supprimer",
        "admin.catalogue.confirm_delete_category": "Supprimer cette categorie ? Les produits resteront sans categorie.",
        "admin.catalogue.empty.title": "Aucune categorie",
        "admin.catalogue.empty.body": "Ajoute un rayon pour commencer a construire le catalogue.",
        "admin.category.kicker": "Categorie",
        "admin.category.add_title": "Ajouter une categorie",
        "admin.category.add_subtitle": "Un seul formulaire, sans autre bloc autour.",
        "admin.category.new_placeholder": "Nouvelle categorie",
        "admin.category.save": "Ajouter la categorie",
        "admin.category.edit_title": "Modifier la categorie",
        "admin.category.edit_subtitle": "{count} produit(s) utilisent actuellement ce rayon.",
        "admin.category.back": "Retour au catalogue",
        "admin.category.empty_products_title": "Aucun produit dans ce rayon",
        "admin.category.empty_products_body": "Tu peux en ajouter un depuis le menu si besoin.",
        "admin.category.no_open_title": "Aucune categorie ouverte",
        "admin.category.no_open_body": "Choisis une categorie dans le catalogue pour afficher ses produits.",
        "admin.products.choose_category": "Choisir une categorie",
        "admin.products.choose_category_subtitle": "Choisis le rayon dont tu veux voir les produits.",
        "admin.products.search_categories": "Rechercher une categorie",
        "admin.products.search_products": "Rechercher un produit dans ce rayon",
        "admin.products.no_search_results": "Aucun resultat pour cette recherche.",
        "admin.product.kicker": "Produit",
        "admin.product.add_title": "Ajouter un produit",
        "admin.product.add_subtitle": "Un seul formulaire, sans catalogue autour.",
        "admin.product.view_catalogue": "Voir le catalogue",
        "admin.product.edit_title": "Modifier le produit",
        "admin.product.edit_subtitle": "Mettre a jour le produit, son image et sa quantite.",
        "admin.product.name_placeholder": "Nom du produit",
        "admin.product.description_placeholder": "Description",
        "admin.product.price_placeholder": "Prix DH",
        "admin.product.stock_placeholder": "Quantite disponible (facultatif)",
        "admin.product.category_placeholder": "Categorie",
        "admin.product.without_category": "Sans categorie",
        "admin.product.select_category": "Choisir une categorie",
        "admin.product.available": "Disponible",
        "admin.product.save": "Ajouter le produit",
        "admin.product.save_changes": "Enregistrer les modifications",
        "admin.product.current_image": "Image actuelle : {image}",
        "admin.product.visible": "Visible",
        "admin.product.hidden": "Masque",
        "admin.product.show": "Afficher",
        "admin.product.hide": "Masquer",
        "admin.product.category_count": "{count} produit{suffix}",
        "admin.product.no_category": "Sans categorie",
        "admin.product.no_products": "Aucun produit",
        "admin.product.no_products_body": "Ajoute des produits pour lancer la vitrine.",

        # Edit pages / generic
        "admin.edit_category.title": "Modifier la categorie",
        "admin.edit_category.subtitle": "{count} produit(s) utilisent actuellement ce rayon.",
        "admin.edit_category.input": "Nom de la categorie",
        "admin.edit_product.return": "Retour au catalogue",

        # Validation / flash messages
        "flash.login_invalid": "Identifiants incorrects.",
        "flash.category_name_required": "Le nom de la categorie est obligatoire.",
        "flash.category_added": "Categorie ajoutee.",
        "flash.category_exists": "Cette categorie existe deja.",
        "flash.category_not_found": "Categorie introuvable.",
        "flash.category_updated": "Categorie modifiee.",
        "flash.category_deleted": "Categorie supprimee.",
        "flash.category_delete_requires_reassignment": "Impossible de supprimer cette categorie tant qu'elle contient des produits. Assignez-les d'abord a une autre categorie.",
        "flash.product_name_price_required": "Nom et prix valides obligatoires.",
        "flash.product_category_required": "Un produit doit obligatoirement appartenir a une categorie.",
        "flash.admin_credentials_required": "Le nom d'utilisateur et le mot de passe sont obligatoires.",
        "flash.admin_access_denied": "Seul le compte principal peut gerer les autres administrateurs.",
        "flash.admin_exists": "Ce compte administrateur existe deja.",
        "flash.admin_already_exists": "Le compte principal est deja utilise.",
        "flash.admin_created": "Le second administrateur a ete cree.",
        "flash.admin_deleted": "Compte supprime.",
        "flash.admin_updated": "Compte modifie.",
        "flash.admin_not_found": "Compte introuvable.",
        "flash.admin_primary_cannot_be_deleted": "Le compte principal ne peut pas etre supprime.",
        "flash.product_added": "Produit ajoute.",
        "flash.product_not_found": "Produit introuvable.",
        "flash.product_updated": "Produit modifie.",
        "flash.product_deleted": "Produit supprime.",
        "validation.stock_integer": "La quantite doit etre un nombre entier.",
        "validation.image_format": "Format d'image non autorise. JPG, PNG, WEBP et GIF seulement.",

        # JavaScript UI strings
        "js.search.loading": "Recherche en cours...",
        "js.search.unavailable": "La recherche est temporairement indisponible.",
        "js.search.no_results": "Aucun resultat pour {query}. Essayez un autre mot-cle.",
        "js.search.categories": "Categories",
        "js.search.products": "Produits",
        "js.search.category_count": "{count} produit{suffix}",
        "js.search.stock_available": "{count} en stock",
        "js.cart.max_quantity": "Quantite maximale atteinte pour ce produit.",
        "js.cart.out_of_stock": "Ce produit est en rupture de stock.",
        "js.cart.added": "{name} a ete ajoute au panier.",
        "js.cart.removed": "Produit supprime du panier.",
        "js.cart.empty": "Votre panier est vide.",
        "js.cart.empty_already": "Votre panier est deja vide.",
        "js.cart.clear_confirm": "Vider le panier ?",
        "js.cart.cleared": "Panier vide.",
        "js.cart.checkout_intro": "Bonjour {shop_name}, je souhaite passer cette commande :",
        "js.cart.total": "Total : {total}",
        "js.cart.name": "Nom : {name}",
        "js.cart.address": "Adresse : {address}",
        "js.cart.confirm": "Merci de confirmer ma commande.",
        "js.cart.unit": "unite",
        "js.cart.stock_available_short": "{count} dispo",
        "js.cart.stock_out": "Rupture",
        "js.cart.explore": "Explorer le catalogue",
        "js.menu.open": "Ouvrir le menu",
        "js.menu.close": "Fermer le menu",
        "js.quick_return.products": "Produits",
        "js.quick_return.search": "Recherche",
        "js.modal.product": "Produit",
        "js.modal.no_description": "Aucune description disponible.",
        "js.modal.close": "Fermer",
    },
    "ar": {
        # Common
        "common.home": "الرئيسية",
        "common.back_home": "العودة إلى الصفحة الرئيسية",
        "common.back_catalogue": "العودة إلى الكتالوج",
        "common.save": "حفظ",
        "common.save_changes": "حفظ التعديلات",
        "common.modify": "تعديل",
        "common.delete": "حذف",
        "common.cancel": "إلغاء",
        "common.confirm": "تأكيد",
        "common.more": "عرض المزيد",
        "common.add": "إضافة",
        "common.remove": "إزالة",
        "common.loading": "جاري التحميل...",
        "common.search": "بحث",
        "common.clear": "مسح",
        "common.language": "اللغة",
        "common.contact": "تواصل معنا",
        "common.out_of_stock": "نفد المخزون",
        "common.in_stock": "متوفر",
        "common.without_category": "بدون فئة",
        "common.visible": "مرئي",
        "common.hidden": "مخفي",
        "common.available": "متاح",
        "common.unavailable": "غير متاح",
        "common.quantity": "الكمية",
        "common.total": "المجموع",
        "common.unit": "وحدة",
        "common.address": "العنوان",
        "common.follow_us": "تابعنا",
        "common.categories": "الفئات",
        "common.products": "المنتجات",
        "common.product": "منتج",

        # Public app
        "app.meta_description": "منتجات مختارة وطلب سريع عبر واتساب.",
        "brand.tagline": "طلب سريع وخدمة مباشرة",
        "brand.logo_alt": "شعار {shop_name}",
        "nav.cart": "السلة",
        "nav.open_menu": "فتح القائمة",
        "nav.close_menu": "إغلاق القائمة",
        "pwa.install": "تثبيت التطبيق",
        "nav.open_admin_menu": "فتح قائمة الإدارة",
        "footer.quick_order": "طلب سريع",
        "footer.write_whatsapp": "اكتب لنا على واتساب لطلبك خلال ثوانٍ.",
        "footer.whatsapp_button": "اطلب عبر واتساب",
        "footer.reply_note": "رد مباشر وطلب مبسط.",
        "footer.address_label": "العنوان",
        "footer.follow_label": "تابعنا",
        "footer.facebook": "فيسبوك",
        "footer.instagram": "إنستغرام",
        "modal.see_more": "عرض المزيد",
        "modal.product": "منتج",
        "modal.close": "إغلاق",
        "modal.no_description": "لا يوجد وصف متاح.",
        "home.page_title": "الرئيسية",
        "home.hero.title": "تشكيلة متنوعة، بطلب خلال ثوانٍ.",
        "home.hero.subtitle": "اكتشف منتجاتنا واطلب بسرعة عبر واتساب.",
        "home.hero.cta.products": "اكتشف المتجر",
        "home.hero.cta.whatsapp": "واتساب",
        "home.search.placeholder": "ابحث عن منتج أو فئة",
        "home.search.aria": "بحث فوري",
        "home.categories.eyebrow": "فئاتنا",
        "home.categories.title": "اختر القسم المناسب",
        "home.categories.active": "الفئة النشطة",
        "home.categories.view_products": "عرض المنتجات",
        "home.categories.empty.title": "لا توجد فئات",
        "home.categories.empty.body": "أضف الفئات من لوحة الإدارة لبدء عرض المتجر.",
        "home.filter.eyebrow": "الفلتر النشط",
        "home.filter.category_prefix": "الفئة",
        "home.filter.search_prefix": "البحث",
        "home.filter.results": "{count} منتج{suffix} تم العثور عليها",
        "home.filter.back": "العودة إلى الصفحة الرئيسية",
        "home.filter.category_selected": "فئة محددة",
        "home.results.by_category": "منتجات الفئة",
        "home.results.by_search": "نتائج البحث",
        "home.results.subtitle.category": "{count} منتج{suffix} داخل هذا القسم.",
        "home.results.subtitle.search": "{count} منتج{suffix} تم العثور عليها.",
        "home.products.empty.title": "لا توجد منتجات",
        "home.products.empty.by_category": "لا توجد منتجات متاحة في هذه الفئة حالياً.",
        "home.products.empty.by_search": "لا توجد نتائج مطابقة لبحثك.",
        "home.products.back": "العودة إلى الصفحة الرئيسية",
        "home.product.no_description": "لا يوجد وصف متاح.",
        "home.product.see_more": "عرض المزيد",
        "home.product.add": "أضف إلى السلة",
        "home.product.out_of_stock": "نفد المخزون",
        "home.product.category_empty": "بدون فئة",

        # Cart page
        "cart.page_title": "السلة",
        "cart.kicker": "السلة",
        "cart.title": "طلبك الحالي",
        "cart.subtitle": "عدّل الكميات، تحقق من المجموع، ثم أرسلها عبر واتساب.",
        "cart.continue": "متابعة التسوق",
        "cart.total_label": "المجموع",
        "cart.order_note": "سيتم إنشاء الرسالة تلقائياً مع تفاصيل كل منتج.",
        "cart.name_label": "اسم الزبون",
        "cart.name_placeholder": "اسمك",
        "cart.address_label": "العنوان أو الحي",
        "cart.address_placeholder": "عنوان التوصيل أو الاستلام",
        "cart.whatsapp": "اطلب عبر واتساب",
        "cart.clear": "إفراغ السلة",
        "cart.empty.title": "سلتك فارغة",
        "cart.empty.body": "أضف منتجات من الكتالوج لإنشاء طلبك.",
        "cart.empty.button": "استعرض الكتالوج",
        "cart.item.unit": "وحدة",
        "cart.item.stock_available": "متوفر {count}",
        "cart.item.stock_out": "نفد المخزون",
        "cart.item.remove": "حذف",
        "cart.confirm_clear": "إفراغ السلة؟",
        "cart.message.intro": "مرحباً {shop_name}، أود تقديم هذا الطلب:",
        "cart.message.total": "المجموع: {total}",
        "cart.message.name": "الاسم: {name}",
        "cart.message.address": "العنوان: {address}",
        "cart.message.confirm": "شكراً لتأكيد طلبي.",
        "js.cart.checkout_unavailable": "تعذر التحقق من الطلب. حاول مرة أخرى بعد لحظات.",

        # Search/live UI
        "search.loading": "جاري البحث...",
        "search.unavailable": "البحث غير متاح مؤقتاً.",
        "search.no_results": "لا توجد نتائج لـ {query}. جرّب كلمة أخرى.",
        "search.categories": "الفئات",
        "search.products": "المنتجات",
        "search.product_stock": "متوفر {count}",

        # Quick return
        "quick_return.kicker": "عودة سريعة",
        "quick_return.products": "المنتجات",
        "quick_return.search": "البحث",

        # Admin
        "admin.space": "مساحة الإدارة",
        "admin.open_menu": "فتح قائمة الإدارة",
        "admin.logout": "تسجيل الخروج",
        "admin.menu.overview": "نظرة سريعة",
        "admin.menu.catalogue": "الكتالوج",
        "admin.menu.add_category": "إضافة فئة",
        "admin.menu.admins": "المشرفون",
        "admin.menu.products": "منتجات القسم",
        "admin.menu.add_product": "إضافة منتج",
        "admin.admins.kicker": "المشرفون",
        "admin.admins.title": "إنشاء مشرف ثانٍ",
        "admin.admins.subtitle": "أضف حساباً إدارياً إضافياً لمشاركة إدارة الموقع.",
        "admin.admins.primary_label": "الحساب الرئيسي",
        "admin.admins.secondary_label": "حساب ثانٍ",
        "admin.admins.username": "اسم المستخدم",
        "admin.admins.password": "كلمة المرور",
        "admin.admins.new_password": "كلمة المرور الجديدة (اختيارية)",
        "admin.admins.submit": "إنشاء المشرف",
        "admin.admins.update": "تعديل",
        "admin.admins.delete": "حذف",
        "admin.admins.confirm_delete": "هل تريد حذف هذا الحساب الإداري؟",
        "admin.admins.empty.title": "لا يوجد مشرف ثانٍ",
        "admin.admins.empty.body": "يمكنك إضافة حساب آخر من هذا النموذج.",
        "admin.login.title": "الإدارة",
        "admin.login.subtitle": "سجّل الدخول لإدارة الكتالوج والفئات والمنتجات.",
        "admin.login.username": "اسم المستخدم",
        "admin.login.password": "كلمة المرور",
        "admin.login.submit": "تسجيل الدخول",
        "admin.login.back": "العودة إلى الموقع",
        "admin.overview.kicker": "نظرة سريعة",
        "admin.overview.title": "الصفحة الرئيسية للإدارة",
        "admin.overview.subtitle": "نظرة سريعة، ثم تفتح فقط ما تحتاجه.",
        "admin.stats.categories": "الفئات",
        "admin.stats.products": "المنتجات",
        "admin.stats.visible": "مرئية",
        "admin.stats.sold_out": "نفدت",
        "admin.stats.today_visits": "الزيارات اليوم",
        "admin.visits.kicker": "الزيارات",
        "admin.visits.title": "عدد الزوار يومياً",
        "admin.visits.subtitle": "تتبع زيارات الموقع الأخيرة.",
        "admin.visits.empty.title": "لا توجد زيارات",
        "admin.visits.empty.body": "ستظهر الإحصاءات هنا بمجرد وصول الزوار إلى الموقع.",
        "admin.quick_catalogue": "الكتالوج",
        "admin.quick_catalogue_sub": "عرض الفئات",
        "admin.quick_add_category": "إضافة فئة",
        "admin.quick_add_category_sub": "إنشاء قسم",
        "admin.quick_products": "المنتجات",
        "admin.quick_products_sub": "فتح قسم",
        "admin.quick_add_product": "إضافة منتج",
        "admin.quick_add_product_sub": "إنشاء عنصر",
        "admin.catalogue.kicker": "الكتالوج",
        "admin.catalogue.title": "الفئات",
        "admin.catalogue.subtitle": "اضغط على فئة لعرض منتجاتها فقط.",
        "admin.catalogue.add_category": "إضافة فئة",
        "admin.catalogue.modify": "تعديل",
        "admin.catalogue.delete": "حذف",
        "admin.catalogue.confirm_delete_category": "حذف هذه الفئة؟ ستبقى المنتجات بدون فئة.",
        "admin.catalogue.empty.title": "لا توجد فئات",
        "admin.catalogue.empty.body": "أضف قسمًا لبدء بناء الكتالوج.",
        "admin.category.kicker": "فئة",
        "admin.category.add_title": "إضافة فئة",
        "admin.category.add_subtitle": "نموذج واحد فقط، بدون أي كتل إضافية.",
        "admin.category.new_placeholder": "فئة جديدة",
        "admin.category.save": "إضافة الفئة",
        "admin.category.edit_title": "تعديل الفئة",
        "admin.category.edit_subtitle": "{count} منتج(ات) تستخدم هذه الفئة حالياً.",
        "admin.category.back": "العودة إلى الكتالوج",
        "admin.category.empty_products_title": "لا توجد منتجات في هذا القسم",
        "admin.category.empty_products_body": "يمكنك إضافة منتج من القائمة إذا لزم الأمر.",
        "admin.category.no_open_title": "لا توجد فئة مفتوحة",
        "admin.category.no_open_body": "اختر فئة من الكتالوج لعرض منتجاتها.",
        "admin.products.choose_category": "اختر فئة",
        "admin.products.choose_category_subtitle": "اختر القسم الذي تريد رؤية منتجاته.",
        "admin.products.search_categories": "البحث عن فئة",
        "admin.products.search_products": "البحث عن منتج في هذا القسم",
        "admin.products.no_search_results": "لا توجد نتائج لهذا البحث.",
        "admin.product.kicker": "منتج",
        "admin.product.add_title": "إضافة منتج",
        "admin.product.add_subtitle": "نموذج واحد فقط، بدون كتالوج حوله.",
        "admin.product.view_catalogue": "عرض الكتالوج",
        "admin.product.edit_title": "تعديل المنتج",
        "admin.product.edit_subtitle": "تحديث المنتج وصورته وكميته.",
        "admin.product.name_placeholder": "اسم المنتج",
        "admin.product.description_placeholder": "الوصف",
        "admin.product.price_placeholder": "السعر DH",
        "admin.product.stock_placeholder": "الكمية المتاحة (اختياري)",
        "admin.product.category_placeholder": "الفئة",
        "admin.product.without_category": "بدون فئة",
        "admin.product.select_category": "اختر فئة",
        "admin.product.available": "متاح",
        "admin.product.save": "إضافة المنتج",
        "admin.product.save_changes": "حفظ التعديلات",
        "admin.product.current_image": "الصورة الحالية: {image}",
        "admin.product.visible": "مرئي",
        "admin.product.hidden": "مخفي",
        "admin.product.show": "إظهار",
        "admin.product.hide": "إخفاء",
        "admin.product.category_count": "{count} منتج{suffix}",
        "admin.product.no_category": "بدون فئة",
        "admin.product.no_products": "لا توجد منتجات",
        "admin.product.no_products_body": "أضف منتجات لتشغيل الواجهة.",

        # Edit pages / generic
        "admin.edit_category.title": "تعديل الفئة",
        "admin.edit_category.subtitle": "{count} منتج(ات) تستخدم هذه الفئة حالياً.",
        "admin.edit_category.input": "اسم الفئة",
        "admin.edit_product.return": "العودة إلى الكتالوج",

        # Validation / flash messages
        "flash.login_invalid": "بيانات الدخول غير صحيحة.",
        "flash.category_name_required": "اسم الفئة مطلوب.",
        "flash.category_added": "تمت إضافة الفئة.",
        "flash.category_exists": "هذه الفئة موجودة بالفعل.",
        "flash.category_not_found": "الفئة غير موجودة.",
        "flash.category_updated": "تم تعديل الفئة.",
        "flash.category_deleted": "تم حذف الفئة.",
        "flash.category_delete_requires_reassignment": "لا يمكن حذف هذه الفئة إلا بعد نقل منتجاتها إلى فئة أخرى.",
        "flash.product_name_price_required": "الاسم والسعر الصحيحان مطلوبان.",
        "flash.product_category_required": "يجب أن ينتمي كل منتج إلى فئة واحدة على الأقل.",
        "flash.admin_credentials_required": "اسم المستخدم وكلمة المرور مطلوبان.",
        "flash.admin_access_denied": "يمكن فقط للحساب الرئيسي إدارة الحسابات الإدارية الأخرى.",
        "flash.admin_exists": "هذا الحساب الإداري موجود بالفعل.",
        "flash.admin_already_exists": "الحساب الرئيسي مستخدم بالفعل.",
        "flash.admin_created": "تم إنشاء المسؤول الثاني.",
        "flash.admin_deleted": "تم حذف الحساب.",
        "flash.admin_updated": "تم تعديل الحساب.",
        "flash.admin_not_found": "الحساب غير موجود.",
        "flash.admin_primary_cannot_be_deleted": "لا يمكن حذف الحساب الرئيسي.",
        "flash.product_added": "تمت إضافة المنتج.",
        "flash.product_not_found": "المنتج غير موجود.",
        "flash.product_updated": "تم تعديل المنتج.",
        "flash.product_deleted": "تم حذف المنتج.",
        "validation.stock_integer": "يجب أن تكون الكمية عدداً صحيحاً.",
        "validation.image_format": "صيغة الصورة غير مسموحة. JPG وPNG وWEBP وGIF فقط.",

        # JavaScript UI strings
        "js.search.loading": "جاري البحث...",
        "js.search.unavailable": "البحث غير متاح مؤقتاً.",
        "js.search.no_results": "لا توجد نتائج لـ {query}. جرّب كلمة أخرى.",
        "js.search.categories": "الفئات",
        "js.search.products": "المنتجات",
        "js.search.category_count": "{count} منتج{suffix}",
        "js.search.stock_available": "{count} متوفر",
        "js.cart.max_quantity": "تم الوصول إلى الحد الأقصى لهذا المنتج.",
        "js.cart.out_of_stock": "هذا المنتج نفد من المخزون.",
        "js.cart.added": "تمت إضافة {name} إلى السلة.",
        "js.cart.removed": "تم حذف المنتج من السلة.",
        "js.cart.empty": "سلتك فارغة.",
        "js.cart.empty_already": "سلتك فارغة بالفعل.",
        "js.cart.clear_confirm": "إفراغ السلة؟",
        "js.cart.cleared": "تم إفراغ السلة.",
        "js.cart.checkout_intro": "مرحباً {shop_name}، أود تقديم هذا الطلب:",
        "js.cart.total": "المجموع: {total}",
        "js.cart.name": "الاسم: {name}",
        "js.cart.address": "العنوان: {address}",
        "js.cart.confirm": "شكراً لتأكيد طلبي.",
        "js.cart.unit": "وحدة",
        "js.cart.stock_available_short": "متوفر {count}",
        "js.cart.stock_out": "نفد المخزون",
        "js.cart.explore": "استعرض الكتالوج",
        "js.menu.open": "فتح القائمة",
        "js.menu.close": "إغلاق القائمة",
        "js.quick_return.products": "المنتجات",
        "js.quick_return.search": "البحث",
        "js.modal.product": "منتج",
        "js.modal.no_description": "لا يوجد وصف متاح.",
        "js.modal.close": "إغلاق",
    },
}


def normalize_language(language: str | None) -> str:
    candidate = (language or "").strip().lower()
    return candidate if candidate in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def get_locale() -> str:
    if has_request_context():
        return normalize_language(session.get("ui_lang") or request.args.get("lang"))
    return DEFAULT_LANGUAGE


def set_locale(language: str) -> None:
    session["ui_lang"] = normalize_language(language)


def get_text_direction(language: str | None = None) -> str:
    return SUPPORTED_LANGUAGES[normalize_language(language or get_locale())]["dir"]


def get_language_options() -> dict[str, dict[str, str]]:
    return SUPPORTED_LANGUAGES


def translate(key: str, **kwargs) -> str:
    text = get_translation_map().get(key, key)

    if kwargs:
        try:
            text = text.format(**kwargs)
        except Exception:
            pass

    return text


def get_translation_map(language: str | None = None) -> dict[str, str]:
    locale = normalize_language(language or get_locale())
    merged = dict(TRANSLATIONS[DEFAULT_LANGUAGE])
    merged.update(TRANSLATIONS[locale])
    return merged


def get_translation_report() -> dict[str, dict[str, list[str]]]:
    baseline_keys = set(TRANSLATIONS[DEFAULT_LANGUAGE])
    report: dict[str, dict[str, list[str]]] = {}

    for language, translations in TRANSLATIONS.items():
        language_keys = set(translations)
        missing = sorted(baseline_keys - language_keys)
        extra = sorted(language_keys - baseline_keys)

        if missing or extra:
            report[language] = {
                "missing": missing,
                "extra": extra,
            }

    return report


def plural_suffix(count: int | str | None, language: str | None = None) -> str:
    try:
        value = int(count)
    except (TypeError, ValueError):
        value = 0

    if value == 1:
        return ""

    locale = normalize_language(language or get_locale())
    if locale == "ar":
        return "ات"

    return "s"


def safe_redirect_target(candidate: str | None, fallback: str) -> str:
    target = (candidate or "").strip()

    if target.endswith("?"):
        target = target[:-1]

    if not target:
        return fallback

    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc:
        return fallback

    if target.startswith("/"):
        return target

    return fallback
