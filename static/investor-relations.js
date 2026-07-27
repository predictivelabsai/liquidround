function copyRelease() {
    var el = document.getElementById('ir-release-markdown');
    if (!el) return;
    navigator.clipboard.writeText(el.value).then(function() {
        var btn = document.querySelector('.ir-action');
        if (!btn) return;
        var old = btn.textContent;
        btn.textContent = 'Copied';
        setTimeout(function() { btn.textContent = old; }, 1800);
    });
}
