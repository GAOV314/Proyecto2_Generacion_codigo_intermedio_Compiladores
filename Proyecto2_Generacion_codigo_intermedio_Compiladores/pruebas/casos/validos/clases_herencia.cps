class Animal {
    let name: String;

    function constructor(name) {
        this.name = name;
    }

    function speak() {
        print(this.name);
    }
}

class Dog extends Animal {
    let breed: String;

    function constructor(name, breed) {
        this.name = name;
        this.breed = breed;
    }

    function fetch() {
        this.speak();
    }
}

let d = new Dog("Rex", "Labrador");
d.speak();
d.fetch();
print(d.breed);
