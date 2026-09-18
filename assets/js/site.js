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

  // Homepage hero: cross-fade through photos and an on-demand desktop video.
  var heroSlides = Array.prototype.slice.call(document.querySelectorAll(".hero-slide"));
  var reduceMotion = window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (heroSlides.length > 1 && !reduceMotion) {
    var heroSlideIndex = 0;
    var heroPaused = false;
    var heroToggle = document.querySelector(".hero-slideshow-toggle");
    var heroNext = document.querySelector(".hero-slideshow-next");
    var heroTimer;
    var saveData = navigator.connection && navigator.connection.saveData;
    var smallScreen = window.matchMedia && window.matchMedia("(max-width: 700px)").matches;
    var allowHeroVideo = !saveData && !smallScreen;

    var stopHeroVideo = function (slide) {
      if (slide && slide.tagName === "VIDEO") {
        slide.pause();
        slide.currentTime = 0;
      }
    };
    var playHeroVideo = function (slide) {
      if (!allowHeroVideo || !slide || slide.tagName !== "VIDEO") return;
      slide.muted = true;
      slide.play().catch(function () {
        // The poster remains visible if browser autoplay policy blocks playback.
      });
    };
    var prepareNextHeroVideo = function () {
      if (!allowHeroVideo) return;
      var next = heroSlides[(heroSlideIndex + 1) % heroSlides.length];
      if (next && next.tagName === "VIDEO" && next.preload !== "auto") {
        next.preload = "auto";
        next.load();
      }
    };
    var activateHeroSlide = function (nextIndex) {
      stopHeroVideo(heroSlides[heroSlideIndex]);
      heroSlides[heroSlideIndex].classList.remove("is-active");
      heroSlideIndex = nextIndex;
      heroSlides[heroSlideIndex].classList.add("is-active");
      if (!heroPaused && !document.hidden) playHeroVideo(heroSlides[heroSlideIndex]);
      prepareNextHeroVideo();
    };
    var advanceHeroSlide = function () {
      activateHeroSlide((heroSlideIndex + 1) % heroSlides.length);
    };
    var scheduleHeroSlide = function () {
      clearTimeout(heroTimer);
      var duration = Number(heroSlides[heroSlideIndex].getAttribute("data-duration")) || 6000;
      heroTimer = setTimeout(function () {
        if (heroPaused || document.hidden) {
          scheduleHeroSlide();
          return;
        }
        advanceHeroSlide();
        scheduleHeroSlide();
      }, duration);
    };
    prepareNextHeroVideo();
    scheduleHeroSlide();
    if (heroToggle) {
      heroToggle.addEventListener("click", function () {
        heroPaused = !heroPaused;
        if (heroPaused) stopHeroVideo(heroSlides[heroSlideIndex]);
        else playHeroVideo(heroSlides[heroSlideIndex]);
        heroToggle.setAttribute("aria-pressed", heroPaused ? "true" : "false");
        heroToggle.setAttribute("aria-label", heroPaused ? "继续背景图片轮播" : "暂停背景图片轮播");
        heroToggle.innerHTML = heroPaused ? "&#9654;" : "&#10074;&#10074;";
      });
    }
    if (heroNext) {
      heroNext.addEventListener("click", function () {
        advanceHeroSlide();
        scheduleHeroSlide();
      });
    }
    document.addEventListener("visibilitychange", function () {
      if (document.hidden) stopHeroVideo(heroSlides[heroSlideIndex]);
      else if (!heroPaused) playHeroVideo(heroSlides[heroSlideIndex]);
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

  // Photo gallery: two continuously moving rows + lightbox
  var track = document.getElementById("galleryTrack");
  var reverseTrack = document.getElementById("galleryTrackReverse");
  if (track && reverseTrack) {
    var items = Array.prototype.slice.call(track.querySelectorAll(".gallery-item"));
    var carousel = document.getElementById("galleryCarousel");
    var current = 0;
    var reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var pointerActive = false;

    // Keep the source order for the lightbox, while distributing cards evenly.
    items.forEach(function (item, i) {
      item.setAttribute("data-gallery-index", i);
      if (i % 2 === 1) reverseTrack.appendChild(item);
    });

    var rowTracks = [track, reverseTrack];
    var rowStates = [];
    if (!reducedMotion) {
      rowTracks.forEach(function (row, rowIndex) {
        var originals = Array.prototype.slice.call(row.querySelectorAll(".gallery-item"));
        var firstClone = null;
        originals.forEach(function (item) {
          var clone = item.cloneNode(true);
          clone.classList.add("gallery-item--clone");
          clone.setAttribute("aria-hidden", "true");
          row.appendChild(clone);
          if (!firstClone) firstClone = clone;
        });
        rowStates.push({
          row: row,
          first: originals[0],
          clone: firstClone,
          direction: rowIndex === 0 ? 1 : -1,
          cycle: 0,
          position: 0
        });
      });

      var measureRows = function () {
        rowStates.forEach(function (state) {
          state.cycle = state.clone.offsetLeft - state.first.offsetLeft;
          if (state.direction < 0 && state.position <= 1) state.position = state.cycle;
          if (state.position > state.cycle) state.position %= state.cycle;
          state.row.scrollLeft = state.position;
        });
      };
      requestAnimationFrame(measureRows);
      window.addEventListener("resize", measureRows);

      var lastFrame = 0;
      var moveRows = function (time) {
        var elapsed = lastFrame ? Math.min(time - lastFrame, 50) : 0;
        lastFrame = time;
        var paused = document.hidden || pointerActive || carousel.contains(document.activeElement);
        if (!paused) {
          rowStates.forEach(function (state) {
            if (!state.cycle) return;
            state.position += state.direction * elapsed * 0.035;
            if (state.direction > 0 && state.position >= state.cycle) {
              state.position -= state.cycle;
            } else if (state.direction < 0 && state.position <= 0) {
              state.position += state.cycle;
            }
            state.row.scrollLeft = state.position;
          });
        }
        requestAnimationFrame(moveRows);
      };
      requestAnimationFrame(moveRows);
    }

    carousel.addEventListener("pointerdown", function () { pointerActive = true; });
    var resumeRows = function () {
      rowStates.forEach(function (state) { state.position = state.row.scrollLeft; });
      pointerActive = false;
    };
    window.addEventListener("pointerup", resumeRows);
    window.addEventListener("pointercancel", resumeRows);

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
    Array.prototype.forEach.call(carousel.querySelectorAll(".gallery-item"), function (it) {
      it.addEventListener("click", function () {
        openLightbox(Number(it.getAttribute("data-gallery-index")));
      });
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
  }

  // Commitment cards: auto-flip one card every 6 seconds once in view,
  // skipped for a cycle if the user has interacted with the cards.
  var commitWrap = document.querySelector(".commit-wrap");
  if (commitWrap) {
    var cards = Array.prototype.slice.call(commitWrap.querySelectorAll(".commit-card"));
    var interacted = false;
    var flipIndex = 0;
    cards.forEach(function (c) {
      ["mouseenter", "touchstart", "focus"].forEach(function (ev) {
        c.addEventListener(ev, function () { interacted = true; }, { passive: true });
      });
    });

    reduceMotion = window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    var demo = function () {
      if (interacted || reduceMotion || !cards.length) {
        interacted = false;
        return;
      }
      var card = cards[flipIndex % cards.length];
      card.classList.add("auto-flip");
      setTimeout(function () {
        card.classList.remove("auto-flip");
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
