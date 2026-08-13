package com.cherry;
import java.util.Scanner;
import java.sql.SQLOutput;

public class Main {
    public static void main(String[]args){
        Scanner sc=new Scanner(System.in);
        int n= sc.nextInt();
        if (n==1 || n==2){
            System.out.println("1");
            return;
        }
        int a=1,b=1,f=0;
        for (int i=3;i<=n;i++){
            f=a+b;
            a=b;
            b=f;
        }
        System.out.println(b);
    }
}

