
function filterContent(content) {
    // Remove the first and last quotation marks.
    content = content && content.trim().replace(/^(["'])|(["'])$/g, '');
    return content;
};

