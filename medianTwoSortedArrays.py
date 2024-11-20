# class Solution:
def findMedianSortedArrays(nums1: list[int], nums2: list[int]) -> float:
    combinedArray = nums1 + nums2
    combinedArray.sort()
    arraymid = len(combinedArray) // 2
    if (len(combinedArray) % 2) == 0:
        return (combinedArray[arraymid] + combinedArray[arraymid - 1]) / 2
    else:
        return combinedArray[arraymid]

nums1 = [1,2]
nums2 = [3,4]
median = findMedianSortedArrays(nums1, nums2)
print(median)