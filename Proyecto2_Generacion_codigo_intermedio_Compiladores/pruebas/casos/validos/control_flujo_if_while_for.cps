let i = 0;
while (i < 10) {
    i = i + 1;
    if (i == 5) {
        continue;
    }
    if (i == 8) {
        break;
    }
    print(i);
}

for (let j = 0; j < 3; j = j + 1) {
    print(j);
}

if (i > 0) {
    print(1);
} else {
    print(0);
}
