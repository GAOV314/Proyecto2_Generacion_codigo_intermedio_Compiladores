// ERROR: espera 2 argumento(s) pero se pasaron 1
class Point {
    let x: Int;
    let y: Int;

    function constructor(x, y) {
        this.x = x;
        this.y = y;
    }
}

let p = new Point(1);
