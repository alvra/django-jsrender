function html_escape(string) {
    if (typeof string !== 'string') {
        if (string == null) {
            return '';
        } else {
            string = string.toString();
        }
    }

    var escape_chars = /[&<>"'`=]/g;
    var escape_replacements = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#x27;',
        '`': '&#x60;',
        '=': '&#x3D;'
    };
    function escape_single_char(chr) {
        return escape_replacements[chr];
    }
    return string.replace(escape_chars, escape_single_char);
}
