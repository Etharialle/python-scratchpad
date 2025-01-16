const words1 = ["hello","leetcode"];
const order1 = "hlabcdefgijkmnopqrstuvwxyz";
const words2 = ["word","world","row"];
const order2 = "worldabcefghijkmnpqstuvxyz";
const words3 = ["apple","app"];
const order3 = "abcdefghijklmnopqrstuvwxyz";

const dictionaryLength = order1.length;

//Create dictionary for translation
const dictionary1 = {};
for(let i = 0; i < dictionaryLength; i++) {
    dictionary1[order1[i]] = i+1;
}

const words1Split = [];
words1.forEach(e => {
    const splitWords = e.split('');
    words1Split.push(splitWords);
});

console.log(words1Split);
const words1Length = []
words1Split.forEach(e => {
    words1Length.push(e.length);
});
const words1Max = Math.max(...words1Length);
console.log(words1Max);

for (let i = 0; i < words1Split.length; i++) {
    let n = words1Split[i].length;
    while(n < words1Max) {
        words1Split[i].push(0);
        n++;
    }
};
console.log(words1Split);

for (let i = 0; i < words1Split.length; i++) {
    for(let j = 0; j < words1Max; j++) {
        if (words1Split[i][j] === 0) continue;
        let letter = words1Split[i][j];
        words1Split[i][j] = dictionary1[letter];
    }
}

console.log(words1Split);