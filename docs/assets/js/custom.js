// h4, h5, h6 제목 크기 강제 적용 JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // h4 제목들 찾아서 강제로 스타일 적용
    const h4Elements = document.querySelectorAll('h4');
    h4Elements.forEach(function(element) {
        element.style.fontSize = '1.2em';
        element.style.fontWeight = '600';
        element.style.color = '#34495e';
        element.style.marginTop = '1em';
        element.style.marginBottom = '0.5em';
        element.style.lineHeight = '1.4';
    });
    
    // h5 제목들 찾아서 강제로 스타일 적용
    const h5Elements = document.querySelectorAll('h5');
    h5Elements.forEach(function(element) {
        element.style.fontSize = '1.2em';
        element.style.fontWeight = '600';
        element.style.color = '#2c3e50';
        element.style.marginTop = '1em';
        element.style.marginBottom = '0.5em';
        element.style.lineHeight = '1.4';
    });
    
    // h6 제목들 찾아서 강제로 스타일 적용
    const h6Elements = document.querySelectorAll('h6');
    h6Elements.forEach(function(element) {
        element.style.fontSize = '1.2em';
        element.style.fontWeight = '600';
        element.style.color = '#34495e';
        element.style.marginTop = '1em';
        element.style.marginBottom = '0.5em';
        element.style.lineHeight = '1.4';
    });
    
    console.log('제목 크기 강제 적용 완료:', {
        h4: h4Elements.length,
        h5: h5Elements.length,
        h6: h6Elements.length
    });
});
