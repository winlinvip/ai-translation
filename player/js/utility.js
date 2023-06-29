
function filterContent(content) {
    // Remove the first and last quotation marks.
    content = content && content.trim().replace(/^(["'])|(["'])$/g, '');
    return content;
};

function scrollToSegment(scrollableDiv, tr) {
    scrollableDiv.animate({
        scrollTop: tr.offset().top - scrollableDiv.offset().top + scrollableDiv.scrollTop()
            - scrollableDiv.height() / 2 + tr.height() / 2
    }, 1000);
}

