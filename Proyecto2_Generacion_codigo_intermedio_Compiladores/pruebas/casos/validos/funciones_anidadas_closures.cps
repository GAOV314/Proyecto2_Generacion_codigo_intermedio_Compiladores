function outer(x) {
    function inner(y) {
        return x + y;
    }
    return inner(10);
}

let r = outer(5);
print(r);
