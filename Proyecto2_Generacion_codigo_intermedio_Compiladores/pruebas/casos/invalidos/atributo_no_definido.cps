// ERROR: no tiene el atributo 'z'
class Point {
    let x: Int;

    function constructor(x) {
        this.x = x;
    }
}

let p = new Point(1);
print(p.z);
