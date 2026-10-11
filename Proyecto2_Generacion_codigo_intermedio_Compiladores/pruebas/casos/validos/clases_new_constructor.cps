class Point {
    let x: Int;
    let y: Int;

    function constructor(x, y) {
        this.x = x;
        this.y = y;
    }

    function sum() {
        return this.x + this.y;
    }
}

let p = new Point(3, 4);
let s = p.sum();
print(s);
print(p.x);
