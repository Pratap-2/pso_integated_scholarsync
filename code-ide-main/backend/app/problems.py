problems = {
    1: {
        "title": "Lexicographically Smallest Permutation with Portals",
        "difficulty": "Hard",

        "description": """
You are given a permutation p of length n and two portals placed at positions x and y (x < y).

A portal at position i lies between the i-th and (i+1)-th elements.

If i = 0, the portal is before the first element.
If i = n, the portal is after the last element.

You may perform these operations any number of times:

1. Remove the element immediately to the LEFT of one portal and insert it to the RIGHT of the other portal.
2. Remove the element immediately to the RIGHT of one portal and insert it to the LEFT of the other portal.

Your goal is to produce the lexicographically smallest permutation possible.
""",

        "aiContext": """
Think about splitting the array into three regions:
left of x, between x and y, and right of y.
Consider which elements can move between portals.
""",

        "solution": """
#include <bits/stdc++.h>
using namespace std;
#define int long long

#define in(a) int a; cin>>a
#define in2(a,b) int a,b;cin>>a>>b
#define in3(a,b,c) int a,b,c;cin>>a>>b>>c

#define all(v) v.begin(), v.end()

#define get(v,n) vector<int> v(n);\\\\
for(int &x:v) cin>>x;

#define fastio ios::sync_with_stdio(false); cin.tie(0); cout.tie(0);

void yesyoucan(){
    in3(n,x,y);
    get(v,n);

    vector<int> l,r;

    for(int i=0;i<x;i++) l.push_back(v[i]);
    for(int i=y;i<n;i++) l.push_back(v[i]);

    int idx=-1, mn=INT_MAX;

    for(int i=x;i<y;i++){
        if(v[i]<mn){
            mn=v[i];
            idx=i;
        }
    }

    for(int i=idx;i<y;i++) r.push_back(v[i]);
    for(int i=x;i<idx;i++) r.push_back(v[i]);

    int pos=-1;

    for(int i=0;i<l.size();i++){
        if(r.size()>0 && l[i]>r[0]){
            pos=i;
            break;
        }
    }

    if(pos==-1) pos=l.size();

    for(int i=0;i<pos;i++) cout<<l[i]<<" ";
    for(int i=0;i<r.size();i++) cout<<r[i]<<" ";
    for(int i=pos;i<l.size();i++) cout<<l[i]<<" ";

    cout<<endl;
}

int32_t main(){
    fastio;
    int t;
    cin>>t;
    while(t--){
        yesyoucan();
    }
}
"""
    }
}
