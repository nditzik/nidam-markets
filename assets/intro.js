/* np164 (30.10.2026, איציק): פתיח הלוגו — מוקאפ https://claude.ai/artifact/JnX8gsX4TbSwaXgXUQczdx
   (נבחר: חיתוך באלכסון, תלת-מימד מלא, מהירות רגילה). נטען סינכרונית בתחילת <body>, לפני שהדף מצויר:
   הלוגו האמיתי (assets/logo-full-dark.png) נכנס מהעומק ומסתובב לחזית עם שכבות עומק, ברק עובר עליו,
   קו אור חוצה באלכסון, והחצי העליון עולה והתחתון יורד — מאחור דף הבית כבר נטען.
   מתי: רק בכניסה לבית (בלי hash או #home), פעם אחת לכל ביקור (sessionStorage — גם הרענון האוטומטי
   של checkVersion לא מפעיל שוב). לחיצה / מקש / "דלג" מסיימים מיד. הפחתת תנועה = הופעה רכה בלבד.
   ?intro=1 מפעיל תמיד (בדיקה), ?intro=0 מכבה. דפדפן אוטומטי (navigator.webdriver) — בלי פתיח. */
(function () {
  var KEY = "np-intro-seen", qs = location.search;
  var force = /[?&]intro=1\b/.test(qs);
  if (/[?&]intro=0\b/.test(qs)) return;
  if (!force) {
    if (navigator.webdriver) return;
    var h = (location.hash || "").replace("#", "");
    if (h && h !== "home") return;
    try { if (sessionStorage.getItem(KEY)) return; } catch (e) {}
  }
  try { sessionStorage.setItem(KEY, "1"); } catch (e) {}
  if (!document.body || !Element.prototype.animate) return;

  var LOGO = "assets/logo-full-dark.png";
  var reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  var narrow = window.innerWidth < 640;
  var root = document.createElement("div");
  root.id = "np-intro";
  root.setAttribute("aria-hidden", "true");
  root.innerHTML = '<div class="ni-half ni-top"></div><div class="ni-half ni-bot"></div><div class="ni-blade"><i></i></div>' +
    '<button type="button" class="ni-skip">דלג</button>';
  document.body.insertBefore(root, document.body.firstChild);
  document.documentElement.classList.add("np-intro-on");
  var top = root.querySelector(".ni-top"), bot = root.querySelector(".ni-bot"), blade = root.querySelector(".ni-blade"), bladeLine = root.querySelector(".ni-blade i");
  var running = [], timer = null, done = false;

  function stage(half) {
    var n = narrow ? 9 : 14, step = narrow ? 1.4 : 1.6, html = "";
    for (var i = n; i >= 1; i--) {
      var b = (0.10 + 0.22 * (1 - i / n)).toFixed(3);   // מאחור כהה יותר
      html += '<img class="ni-layer ni-depth" src="' + LOGO + '" alt="" style="transform:translateZ(' + (-i * step) + 'px);filter:brightness(' + b + ') saturate(.55)">';
    }
    html += '<img class="ni-layer ni-front" src="' + LOGO + '" alt=""><div class="ni-sheen"></div>';
    half.innerHTML = '<div class="ni-stage"><div class="ni-rig">' + html + "</div></div>";
    return half.querySelector(".ni-rig");
  }
  function anim(el, kf, o) { var a = el.animate(kf, o); running.push(a); return a; }
  function finish() {
    if (done) return;
    done = true;
    clearTimeout(timer);
    running.forEach(function (a) { try { a.cancel(); } catch (e) {} });
    document.removeEventListener("keydown", finish, true);
    document.documentElement.classList.remove("np-intro-on");
    if (root.parentNode) root.parentNode.removeChild(root);
  }
  root.addEventListener("click", finish);
  document.addEventListener("keydown", finish, true);

  if (reduce) {
    anim(root, [{ opacity: 1 }, { opacity: 1, offset: .55 }, { opacity: 0 }], { duration: 1000, fill: "forwards" });
    timer = setTimeout(finish, 1050);
    return;
  }

  // חיתוך באלכסון: 44% בצד אחד, 56% בצד השני; הקו באותה זווית
  // חפיפה של חצי פיקסל-אחוז בין החצאים, כדי שלא ייראה תפר לפני החיתוך
  top.style.clipPath = "polygon(0 0,100% 0,100% 44.4%,0 56.4%)";
  bot.style.clipPath = "polygon(0 55.6%,100% 43.6%,100% 100%,0 100%)";
  var rot = -Math.atan2(window.innerHeight * 0.12, window.innerWidth) * 180 / Math.PI;
  var r1 = stage(top), r2 = stage(bot);

  function play() {
    if (done) return;
    var E = "cubic-bezier(.2,.7,.2,1)";
    [r1, r2].forEach(function (rig) {
      anim(rig, [
        { transform: "translateZ(-260px) rotateX(22deg) rotateY(-48deg)", opacity: 0 },
        { transform: "translateZ(0) rotateX(6deg) rotateY(-14deg)", opacity: 1, offset: .55 },
        { transform: "translateZ(30px) rotateX(3deg) rotateY(-6deg)", opacity: 1 }
      ], { duration: 1500, easing: E, fill: "forwards" });
      anim(rig.querySelector(".ni-sheen"), [
        { opacity: 0, backgroundPosition: "120% 0" }, { opacity: 1, offset: .2 }, { opacity: 0, backgroundPosition: "-20% 0" }
      ], { duration: 700, delay: 950, easing: "ease-in-out", fill: "forwards" });
      anim(rig.querySelector(".ni-front"), [
        { filter: "brightness(1)" }, { filter: "brightness(1.35)", offset: .45 }, { filter: "brightness(1)" }
      ], { duration: 700, delay: 950, easing: "ease-in-out" });
    });
    // הקו מסתובב סביב מרכז המסך (שם עובר האלכסון) ו"נמתח" משמאל לימין
    blade.style.transform = "rotate(" + rot + "deg)";
    anim(bladeLine, [
      { transform: "scaleX(0)", opacity: 1 },
      { transform: "scaleX(1)", opacity: 1, offset: .75 },
      { transform: "scaleX(1)", opacity: 0 }
    ], { duration: 520, delay: 1500, easing: "cubic-bezier(.7,0,.3,1)", fill: "forwards" });
    var split = { duration: 820, delay: 1900, easing: "cubic-bezier(.75,0,.2,1)", fill: "forwards" };
    anim(top, [{ transform: "translateY(0)" }, { transform: "translateY(-104%)" }], split);
    anim(bot, [{ transform: "translateY(0)" }, { transform: "translateY(104%)" }], split);
    timer = setTimeout(finish, 2760);
  }

  // מחכים ללוגו (עד 1.5 שנ'); אם לא נטען — בלי פתיח
  var img = new Image(), started = false;
  function go() { if (!started) { started = true; play(); } }
  img.onload = go;
  img.onerror = finish;
  img.src = LOGO;
  if (img.complete && img.naturalWidth) go();
  setTimeout(function () { if (!started) finish(); }, 1500);
  setTimeout(finish, 6000);   // רשת ביטחון: הפתיח לעולם לא נשאר על המסך
})();
