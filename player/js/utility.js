
function filterContent(content) {
    // Remove the first and last quotation marks.
    content = content && content.trim().replace(/^(["'])|(["'])$/g, '');

    // For fairseq, there is always some noise in the end of the content.
    for (const noise of ['- I know .', '现在,我们要去.']) {
        content = content && content.indexOf(noise) > 0 ? content.split(noise)[0] : content;
    }
    return content;
};

