// given two arrays that are sorted and distinct find the number of common elements

const arr1 = [1,3,4,5,9,12,15,16,25];
const arr2 = [1,3,6,7,9,10,25];

//compare the length of the two arrays
let shortArray;
let longArray;
if (arr1.length <= arr2.length ) {
  shortArray = arr1;
  longArray = arr2;
} else {
  shortArray = arr2;
  longArray = arr1;
}

let numberOfCommonElements = 0;
for (let i = 0; i < shortArray.length; i++) {
  for (let j = 0; j < longArray.length; j++) {
    if (shortArray[i] === longArray[j]) numberOfCommonElements++;
  }
}
console.log(numberOfCommonElements);

// can I make it faster?
// check for if shortArray[i] > longArray[j]