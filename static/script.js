function sendFormData (route, symbol, shares) {
    let xhr = new XMLHttpRequest();
    let body = 'symbol='+encodeURIComponent(symbol)+'&shares='+encodeURIComponent(shares);
    xhr.open("POST", route, true);
    xhr.setRequestHeader('Content-type', 'application/x-www-form-urlencoded');
    xhr.send(body);
}