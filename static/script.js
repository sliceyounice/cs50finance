
function sendFormData(route, element) {
    let xhr = new XMLHttpRequest();
    let symbol = element.closest('tr').getAttribute('datatype');
    let shares = document.getElementById('shares').value;
    let body = 'symbol=' + encodeURIComponent(symbol) + '&shares=' + encodeURIComponent(shares);
    xhr.open("POST", route, true);
    xhr.setRequestHeader('Content-type', 'application/x-www-form-urlencoded');
    xhr.send(body);
    xhr.onload = function () {
        location.reload();
    }
}

document.querySelector('#buy').addEventListener('click', function () {
    sendFormData('/buy', this);
});
document.querySelector('#sell').addEventListener('click', function () {
    sendFormData('/sell', this);
});