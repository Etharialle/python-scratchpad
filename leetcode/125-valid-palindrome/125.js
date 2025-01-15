const regexList = /[^a-zA-Z\d]/g;
s = s.toLowerCase();
let stringStrip = s.replace(regexList, '');
let stringSplit = stringStrip.split('');
let arrayReverse = stringSplit.reverse();
let stringReverse = arrayReverse.join('');
if (stringStrip === stringReverse) {
    return true;
} else {
    return false;
}