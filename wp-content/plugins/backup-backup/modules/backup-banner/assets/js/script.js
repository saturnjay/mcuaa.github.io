(function ($) {

  var nonce = bmi_backup_banner.dismiss_nonce;
  var pluginUrl = bmi_backup_banner.plugin_url;  
  // Position the wavy arrow from the banner to the sidebar menu item
  function positionArrow() {
    if (window.innerWidth < 1200) {
      $('#bmi-backup-banner-arrow').hide();
      return;
    }
    var $arrow = $('#bmi-backup-banner-arrow');
    var $banner = $('#bmi-backup-banner');
    var $menuItem = $('#adminmenu').find('li.toplevel_page_backup-migration');

    if (!$menuItem.length || !$arrow.length || !$banner.length) return;

    // Position banner so its bottom is 50px below the menu item's bottom
    var menuRect = $menuItem[0].getBoundingClientRect();
    var bannerRect = $banner[0].getBoundingClientRect();

    // Width = horizontal distance between the menu item's right edge and the banner's left edge
    var arrowWidth = bannerRect.left - menuRect.right + 45;

    if (arrowWidth <= 0) {
      $arrow.hide();
      return;
    }

    // Left of arrow at the right edge of the menu item (bottom border)
    var arrowLeft = menuRect.right - 40;

    // Vertical span: from menu item bottom to banner bottom-left corner
    var arrowTop = menuRect.bottom + 5;

    $arrow.css({
      left: arrowLeft + 'px',
      top: arrowTop + 'px',
      width: arrowWidth + 'px',
      display: 'block'
    });

    // Move banner so its bottom-left corner aligns with the arrow's right end
    var arrowBottom = arrowTop + $arrow[0].getBoundingClientRect().height;
    var bannerHeight = $banner[0].offsetHeight + 8;
    $banner.css({
      top: (arrowBottom - bannerHeight) + 'px',
      transform: 'translateX(-50%)'
    });
  }

  // Reveal banner elements once page is fully loaded
  function showBanner() {
      // Find the Backup Migration sidebar menu item
      var $menuItem = $('#adminmenu').find('li.toplevel_page_backup-migration');

      // Highlight the sidebar menu item (exclude from overlay)
      if ($menuItem.length) {
        $menuItem.addClass('bmi-backup-banner--sidebar-highlight');
      }

      $('#adminmenu li').not('#toplevel_page_backup-migration, #toplevel_page_backup-migration *').each(function () {
          $(this).addClass('bmi-menu-dim');
      });
      $('.wp-menu-separator').css('margin', '0');
    positionArrow();
    $('#bmi-backup-banner-overlay').addClass('bmi-backup-banner--ready');
    $('#bmi-backup-banner').addClass('bmi-backup-banner--ready');
    $('#bmi-backup-banner-arrow').addClass('bmi-backup-banner--ready');

    // Re-emit resize so position is recalculated with transitions now active
    requestAnimationFrame(function () {
      window.dispatchEvent(new Event('resize'));
    });
  }

  $(window).on('resize', positionArrow);

  if (document.readyState === 'complete') {
    showBanner();
  } else {
    $(window).on('load', showBanner);
  }

  // Dismiss helper
  function dismissBanner(callback) {
    $.post(ajaxurl, {
      action: 'dismiss_bmi_backup_banner',
      token: 'bmi_backup_banner',
      nonce: nonce,
    }).done(async function (res) {
      if (callback) await callback();
    }).fail(async function (err) {
      console.error(err);
      if (callback) await callback();
    });
  }

  function hideBanner() {
    var $menuItem = $('#adminmenu').find('li.toplevel_page_backup-migration');
    $('#bmi-backup-banner').hide();
    $('#bmi-backup-banner-overlay').hide();
    $('#bmi-backup-banner-arrow').hide();
    $('.bmi-menu-dim').removeClass('bmi-menu-dim');
    $('#adminmenu, #adminmenuwrap').css('pointer-events', 'auto');
    $menuItem.removeClass('bmi-backup-banner--sidebar-highlight');
    clearInterval(countdownInterval);
  }

  // CTA button: dismiss + redirect to BMI page
  $('.bmi-backup-banner__cta').on('click', function (e) {
    e.preventDefault();
    var href = $(e.currentTarget).attr('href');
    dismissBanner(function () {
      hideBanner();
      if (href) window.location.href = href;
    });
  });

  $('.bmi-backup-banner__install-btn').on('click', function (e) {
    e.preventDefault();
    var href = $(e.currentTarget).attr('href');
    dismissBanner(function () {
      hideBanner();
      if (href) window.open(href, '_blank');
    });
  });
  // Close button: dismiss only
  $('.bmi-backup-banner__close').on('click', function (e) {
    e.preventDefault();
    dismissBanner(function () {
      hideBanner();
    });
  });

  // Clicking the sidebar menu item should also dismiss the banner
  $('#toplevel_page_backup-migration a').on('click', function (e) {
    e.preventDefault();
    var href = $(this).attr('href');
    dismissBanner(function () {
      hideBanner();
      if (href) window.location.href = href;
    });
  });

  function updateCountdown() {
    if (!bmi_backup_banner.expiring_at) {
      $('#changeable-text').text('before it expires!');
      return;
    }

    var remaining = Math.floor(bmi_backup_banner.expiring_at - Date.now() / 1000);

    if (remaining <= 0) {
      $('#changeable-text').text('it has expired!');
      clearInterval(countdownInterval);
      return;
    }

    var hours = Math.floor(remaining / 3600);
    var minutes = Math.floor((remaining % 3600) / 60);

    var text = 'It expires in ';
    if (hours > 0) text += hours + ' hour' + (hours !== 1 ? 's' : '') + ' and ';
    if (hours > 0 || minutes > 0) text += minutes + ' minute' + (minutes !== 1 ? 's' : '');

    $('#changeable-text').text(text);
    positionArrow();
  }

  updateCountdown();
  var countdownInterval = setInterval(updateCountdown, 1000);



})(jQuery);
