(function () {
  "use strict";

  var nav = document.querySelector(".nav");
  var toggle = document.getElementById("navToggle");
  var navInner = document.querySelector(".nav-inner");
  var navLinks = document.querySelector(".nav-links");

  // Solid bar after scrolling past the hero
  var onScroll = function () {
    if (nav) nav.classList.toggle("scrolled", window.scrollY > 60);
  };
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  // Mobile menu
  var toggleMenu = function () {
    if (!navLinks) return;
    var open = navLinks.classList.toggle("open");
    if (navInner) navInner.classList.toggle("open", open);
    if (toggle) toggle.setAttribute("aria-expanded", open ? "true" : "false");
  };
  if (toggle) toggle.addEventListener("click", toggleMenu);
  if (navLinks) {
    navLinks.querySelectorAll("a").forEach(function (a) {
      a.addEventListener("click", function () {
        navLinks.classList.remove("open");
        if (navInner) navInner.classList.remove("open");
      });
    });
  }

  // Scroll reveal
  var reveals = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window && reveals.length) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });
    reveals.forEach(function (el) { io.observe(el); });
  } else {
    reveals.forEach(function (el) { el.classList.add("visible"); });
  }

  // Photo gallery: carousel + lightbox
  var track = document.getElementById("galleryTrack");
  if (track) {
    var items = Array.prototype.slice.call(track.querySelectorAll(".gallery-item"));
    var carousel = document.getElementById("galleryCarousel");
    var prevBtn = document.getElementById("galleryPrev");
    var nextBtn = document.getElementById("galleryNext");
    var dotsWrap = document.getElementById("galleryDots");
    var current = 0;

    var buildDots = function () {
      if (!dotsWrap) return;
      dotsWrap.innerHTML = "";
      items.forEach(function (_, i) {
        var d = document.createElement("button");
        d.className = "gallery-dot";
        d.setAttribute("aria-label", "照片 " + (i + 1));
        d.addEventListener("click", function () {
          current = i;
          scrollTo();
        });
        dotsWrap.appendChild(d);
      });
    };
    var scrollTo = function () {
      var card = items[current];
      if (!card) return;
      // Scroll only the track horizontally; never move the page vertically,
      // so the autoplay cannot yank the viewport back to the gallery.
      var left = card.offsetLeft - track.offsetLeft -
        (track.clientWidth - card.offsetWidth) / 2;
      track.scrollTo({ left: left, behavior: "smooth" });
    };
    var updateDots = function () {
      if (!dotsWrap) return;
      var idx = Math.round(track.scrollLeft / (items[0].offsetWidth + 20));
      idx = Math.max(0, Math.min(items.length - 1, idx));
      current = idx;
      var dots = dotsWrap.children;
      for (var i = 0; i < dots.length; i++) dots[i].classList.toggle("active", i === idx);
    };
    if (prevBtn) prevBtn.addEventListener("click", function () {
      current = Math.max(0, current - 1);
      scrollTo();
    });
    if (nextBtn) nextBtn.addEventListener("click", function () {
      current = Math.min(items.length - 1, current + 1);
      scrollTo();
    });
    track.addEventListener("scroll", updateDots, { passive: true });

    // autoplay (paused while hovering the carousel)
    var auto = setInterval(function () {
      if (document.hidden || carousel.matches(":hover")) return;
      current = (current + 1) % items.length;
      scrollTo();
    }, 4000);

    // lightbox
    var lightbox = document.createElement("div");
    lightbox.className = "lightbox";
    lightbox.innerHTML =
      '<button class="lightbox-close" aria-label="关闭">&times;</button>' +
      '<button class="lightbox-nav lightbox-prev" aria-label="上一张">&lsaquo;</button>' +
      '<img alt=""><figcaption></figcaption>' +
      '<button class="lightbox-nav lightbox-next" aria-label="下一张">&rsaquo;</button>';
    document.body.appendChild(lightbox);
    var lbImg = lightbox.querySelector("img");
    var lbCap = lightbox.querySelector("figcaption");
    var openLightbox = function (i) {
      current = i;
      lbImg.src = items[i].querySelector("img").src;
      lbCap.textContent = items[i].getAttribute("data-caption") || "";
      lightbox.classList.add("open");
      document.body.style.overflow = "hidden";
    };
    var closeLightbox = function () {
      lightbox.classList.remove("open");
      document.body.style.overflow = "";
    };
    items.forEach(function (it, i) {
      it.addEventListener("click", function () { openLightbox(i); });
    });
    lightbox.querySelector(".lightbox-close").addEventListener("click", closeLightbox);
    lightbox.addEventListener("click", function (e) { if (e.target === lightbox) closeLightbox(); });
    lightbox.querySelector(".lightbox-prev").addEventListener("click", function (e) {
      e.stopPropagation();
      openLightbox((current + items.length - 1) % items.length);
    });
    lightbox.querySelector(".lightbox-next").addEventListener("click", function (e) {
      e.stopPropagation();
      openLightbox((current + 1) % items.length);
    });
    document.addEventListener("keydown", function (e) {
      if (!lightbox.classList.contains("open")) return;
      if (e.key === "Escape") closeLightbox();
      if (e.key === "ArrowLeft") openLightbox((current + items.length - 1) % items.length);
      if (e.key === "ArrowRight") openLightbox((current + 1) % items.length);
    });

    buildDots();
    updateDots();
  }

  // Commitment cards: hint + auto-flip one card every 6 seconds once in view,
  // skipped for a cycle if the user has interacted with the cards.
  var commitWrap = document.querySelector(".commit-wrap");
  if (commitWrap) {
    var cards = Array.prototype.slice.call(commitWrap.querySelectorAll(".commit-card"));
    var hint = document.createElement("div");
    hint.className = "commit-hint";
    hint.textContent = "悬停或点击卡片查看英文翻译 · Hover or tap a card to see English";
    commitWrap.insertBefore(hint, commitWrap.querySelector(".commit-cards"));

    var interacted = false;
    var flipIndex = 0;
    cards.forEach(function (c) {
      ["mouseenter", "touchstart", "focus"].forEach(function (ev) {
        c.addEventListener(ev, function () { interacted = true; }, { passive: true });
      });
    });

    var reduceMotion = window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    var demo = function () {
      if (interacted || reduceMotion || !cards.length) {
        interacted = false;
        return;
      }
      hint.classList.add("show");
      var card = cards[flipIndex % cards.length];
      card.classList.add("auto-flip");
      setTimeout(function () {
        card.classList.remove("auto-flip");
        hint.classList.remove("show");
      }, 2600);
      flipIndex++;
    };

    // First demo when the cards scroll into view, then repeat every minute
    var demoStarted = false;
    var startDemo = function () {
      if (demoStarted) return;
      demoStarted = true;
      demo();
      setInterval(demo, 6000);
    };
    if ("IntersectionObserver" in window) {
      var io2 = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) {
            startDemo();
            io2.unobserve(commitWrap);
          }
        });
      }, { threshold: 0.3 });
      io2.observe(commitWrap);
    } else {
      setTimeout(startDemo, 10000);
    }
  }
})();
