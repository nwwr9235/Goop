# 🚂 دليل النشر على Railway

## الخطوة 1 — رفع الكود على GitHub

1. أنشئ مستودعاً جديداً على [github.com](https://github.com/new)
2. ارفع ملفات المشروع:

```bash
git init
git add .
git commit -m "Initial ArabBot deploy"
git remote add origin https://github.com/USERNAME/arabbot.git
git push -u origin main
```

---

## الخطوة 2 — إنشاء مشروع على Railway

1. اذهب إلى [railway.app](https://railway.app) وسجل دخولك
2. اضغط **New Project**
3. اختر **Deploy from GitHub repo**
4. اختر مستودعك

---

## الخطوة 3 — إضافة MongoDB

1. في مشروعك على Railway اضغط **+ New**
2. اختر **Database → Add MongoDB**
3. سيُضاف `MONGO_URL` تلقائياً للـ environment

> **بديل:** استخدم [MongoDB Atlas](https://www.mongodb.com/atlas) مجاناً وانسخ الـ connection string

---

## الخطوة 4 — إضافة المتغيرات (Variables)

في مشروعك على Railway:
1. اضغط على **service** الخاص بالبوت
2. اذهب لتبويب **Variables**
3. أضف هذه المتغيرات واحداً واحداً:

| المتغير | القيمة |
|---------|--------|
| `BOT_TOKEN` | توكن البوت من @BotFather |
| `API_ID` | من https://my.telegram.org |
| `API_HASH` | من https://my.telegram.org |
| `OWNER_ID` | معرّفك الرقمي (اسأل @userinfobot) |
| `DB_NAME` | `arabbot` |
| `MAX_WARNINGS` | `3` |
| `WARN_ACTION` | `mute` |
| `DOWNLOAD_DIR` | `/tmp/arabbot_music` |

> ملاحظة: `MONGO_URL` يُضاف تلقائياً إذا أضفت MongoDB plugin

---

## الخطوة 5 — اختيار طريقة البناء

Railway سيكتشف `Dockerfile.railway` تلقائياً عبر `railway.toml`.

إذا لم يعمل، اذهب لـ **Settings → Build** واختر:
- **Builder:** Dockerfile
- **Dockerfile Path:** `Dockerfile.railway`

---

## الخطوة 6 — النشر

1. اضغط **Deploy** أو ادفع commit جديد لـ GitHub
2. راقب الـ logs في تبويب **Deployments**
3. ابحث عن رسالة: `✅ Bot is online and ready.`

---

## 🔍 استكشاف الأخطاء

### البوت لا يبدأ
```
❌ خطأ: BOT_TOKEN not set
```
← تأكد من إضافة جميع المتغيرات في Variables tab

### خطأ في MongoDB
```
❌ ServerSelectionTimeoutError
```
← تأكد من أن `MONGO_URL` صحيح، أو أضف MongoDB plugin

### خطأ ffmpeg
```
❌ ffmpeg not found
```
← تأكد من استخدام `Dockerfile.railway` وليس Nixpacks

### البوت يعمل لكن الموسيقى لا تشتغل
- البوت يجب أن يكون **مشرفاً** في المجموعة
- يجب أن تكون المحادثة الصوتية **مفتوحة** مسبقاً
- استخدم أمر `تشغيل <اسم أغنية>` والبوت سيدخل تلقائياً

---

## 💰 التكلفة على Railway

| الخطة | التفاصيل |
|--------|---------|
| **Hobby (مجاني)** | $5 رصيد شهري — يكفي للتشغيل المستمر تقريباً |
| **Pro** | $20/شهر — للمجموعات الكبيرة |

> ✅ الـ Hobby plan يكفي لتشغيل البوت مع MongoDB

---

## 🔄 التحديث

لتحديث البوت بعد تعديل الكود:

```bash
git add .
git commit -m "Update bot"
git push
```

Railway سيعيد البناء والنشر تلقائياً.

---

## 🛡 نصائح أمان

- لا ترفع ملف `.env` على GitHub أبداً
- استخدم Railway Variables لجميع البيانات الحساسة
- أضف `.env` إلى `.gitignore`

```bash
echo ".env" >> .gitignore
echo "*.session" >> .gitignore
```
