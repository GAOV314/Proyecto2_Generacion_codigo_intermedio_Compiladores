function factorial(n) {
    if (n <= 1) {
        return 1;
    } else {
        return n * factorial(n - 1);
    }
}

function esPar(n) {
    if (n == 0) {
        return true;
    }
    return esImpar(n - 1);
}

function esImpar(n) {
    if (n == 0) {
        return false;
    }
    return esPar(n - 1);
}

let r = factorial(5);
print(r);
print(esPar(4));
