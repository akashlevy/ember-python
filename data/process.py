lines = open('cb3bpc.csv').readlines()
with open('3bpc.csv', 'w') as outfile:
    for i in range(3):
        for j in range(144*i + 48, 144*(i+1)):
            lines[144*i + j%48] = lines[144*i + j%48].replace('\n', '\t' + '\t'.join(lines[j].split('\t')[2:]))
        outfile.write(''.join(lines[144*i:144*i+48]))
