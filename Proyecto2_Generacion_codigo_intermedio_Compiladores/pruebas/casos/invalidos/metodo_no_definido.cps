// ERROR: no tiene el método 'fly'
class Point {
    let x: Int;

    function constructor(x) {
        this.x = x;
    }
}

let p = new Point(1);
p.fly();
