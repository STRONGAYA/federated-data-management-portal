/**
 * "Download plot" pill buttons: clicking the button toggles its format
 * dropdown; clicking an option downloads the plot of the surrounding tile
 * via Plotly.downloadImage. Purely delegated, so it works for any number of
 * charts without per-chart ids or Dash callbacks.
 */
(function () {
    'use strict';

    function closeAllMenus(except) {
        document.querySelectorAll('.plot-download-menu').forEach(function (menu) {
            if (menu !== except) {
                menu.hidden = true;
            }
        });
    }

    document.addEventListener('click', function (event) {
        var btn = event.target.closest('.plot-download-btn');
        if (btn) {
            var menu = btn.parentElement.querySelector('.plot-download-menu');
            if (menu) {
                menu.hidden = !menu.hidden;
                closeAllMenus(menu);
            }
            return;
        }

        var option = event.target.closest('.plot-download-option');
        if (option) {
            var wrap = option.closest('.plot-download');
            var menu = wrap ? wrap.querySelector('.plot-download-menu') : null;
            if (menu) {
                menu.hidden = true;
            }
            // walk up to the nearest ancestor that contains a plotly graph
            var node = option.parentElement;
            while (node && !node.querySelector('.js-plotly-plot')) {
                node = node.parentElement;
            }
            var gd = node ? node.querySelector('.js-plotly-plot') : null;
            if (gd && window.Plotly) {
                window.Plotly.downloadImage(gd, {
                    format: option.getAttribute('data-format') || 'svg',
                    filename: 'plot',
                    scale: 2
                });
            }
            return;
        }

        // clicking anywhere else closes the menus
        closeAllMenus(null);
    });
})();
