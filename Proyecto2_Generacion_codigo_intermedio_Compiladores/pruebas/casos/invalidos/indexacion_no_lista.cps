// ERROR: no se puede indexar un valor de tipo 'Point'
class Point {
    let x: Int;

    function constructor(x) {
        this.x = x;
    }
}

let p = new Point(1);
let z = p[0];
