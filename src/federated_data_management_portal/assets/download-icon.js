/**
 * Replace plotly's camera icon on the "Download plot" mode bar button with a
 * download arrow, so the control is recognisable at a glance.
 *
 * Plotly draws its built-in mode bar buttons as inline SVG paths and offers
 * no configuration for their icons, so the path is rewritten here. A mutation
 * observer is required because plotly rebuilds the mode bar on every figure
 * update; the applied check keeps the observer from re-mutating indefinitely.
 */
(function () {
    'use strict';

    var DOWNLOAD_VIEWBOX = '0 0 24 24';
    var DOWNLOAD_PATH = 'M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z';

    function applyDownloadIcon(root) {
        var buttons = root.querySelectorAll('.modebar-btn[data-title="Download plot"]');
        Array.prototype.forEach.call(buttons, function (button) {
            var svg = button.querySelector('svg');
            var path = svg ? svg.querySelector('path') : null;
            if (!path || svg.getAttribute('viewBox') === DOWNLOAD_VIEWBOX) {
                return;
            }
            svg.setAttribute('viewBox', DOWNLOAD_VIEWBOX);
            path.setAttribute('d', DOWNLOAD_PATH);
            path.removeAttribute('transform');
        });
    }

    applyDownloadIcon(document);

    var observer = new MutationObserver(function () {
        applyDownloadIcon(document);
    });
    observer.observe(document.body, {childList: true, subtree: true});
})();
