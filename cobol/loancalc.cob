      *> LOANCALC - level-payment (annuity) loan schedule calculator.
      *>
      *> Input  (stdin, one fixed-length record, 22 chars):
      *>   principal   PIC 9(12)       yen
      *>   annual rate PIC 9(2)V9(4)   percent, e.g. 001500 = 1.5000%
      *>   months      PIC 9(4)
      *>
      *> Output (stdout, fixed-length records):
      *>   D + month(4) + payment(12) + principal(12) + interest(12)
      *>     + balance(12)                       one per month
      *>   T + payment(12) + total paid(12) + total interest(12)
      *>   E + error code(2)                     on invalid input
      *>
      *> Interest is truncated to whole yen each month; the final
      *> month absorbs the rounding difference so the balance ends at 0.
       IDENTIFICATION DIVISION.
       PROGRAM-ID. LOANCALC.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  IN-REC.
           05  IN-PRINCIPAL        PIC 9(12).
           05  IN-RATE             PIC 9(2)V9(4).
           05  IN-MONTHS           PIC 9(4).

       01  WS-MONTHLY-RATE         PIC 9V9(15).
       01  WS-FACTOR               PIC 9(9)V9(12).
       01  WS-PAYMENT              PIC 9(12).
       01  WS-BALANCE              PIC 9(12).
       01  WS-INTEREST             PIC 9(12).
       01  WS-PRIN-PART            PIC 9(12).
       01  WS-PAY-THIS             PIC 9(12).
       01  WS-TOTAL-PAID           PIC 9(14) VALUE 0.
       01  WS-TOTAL-INTEREST       PIC 9(14) VALUE 0.
       01  WS-I                    PIC 9(4).

       01  OUT-DETAIL.
           05  FILLER              PIC X VALUE "D".
           05  OD-MONTH            PIC 9(4).
           05  OD-PAYMENT          PIC 9(12).
           05  OD-PRINCIPAL        PIC 9(12).
           05  OD-INTEREST         PIC 9(12).
           05  OD-BALANCE          PIC 9(12).

       01  OUT-TRAILER.
           05  FILLER              PIC X VALUE "T".
           05  OT-PAYMENT          PIC 9(12).
           05  OT-TOTAL-PAID       PIC 9(12).
           05  OT-TOTAL-INTEREST   PIC 9(12).

       01  OUT-ERROR.
           05  FILLER              PIC X VALUE "E".
           05  OE-CODE             PIC X(2).

       PROCEDURE DIVISION.
       MAIN-PARA.
           ACCEPT IN-REC
           PERFORM VALIDATE-INPUT
           PERFORM CALC-PAYMENT
           PERFORM BUILD-SCHEDULE
           MOVE WS-PAYMENT        TO OT-PAYMENT
           MOVE WS-TOTAL-PAID     TO OT-TOTAL-PAID
           MOVE WS-TOTAL-INTEREST TO OT-TOTAL-INTEREST
           DISPLAY OUT-TRAILER
           MOVE 0 TO RETURN-CODE
           STOP RUN.

       VALIDATE-INPUT.
           IF IN-PRINCIPAL IS NOT NUMERIC
              OR IN-RATE IS NOT NUMERIC
              OR IN-MONTHS IS NOT NUMERIC
               MOVE "01" TO OE-CODE
               PERFORM ABORT-WITH-ERROR
           END-IF
           IF IN-PRINCIPAL = 0
               MOVE "02" TO OE-CODE
               PERFORM ABORT-WITH-ERROR
           END-IF
           IF IN-RATE > 20
               MOVE "03" TO OE-CODE
               PERFORM ABORT-WITH-ERROR
           END-IF
           IF IN-MONTHS = 0 OR IN-MONTHS > 600
               MOVE "04" TO OE-CODE
               PERFORM ABORT-WITH-ERROR
           END-IF.

       CALC-PAYMENT.
           COMPUTE WS-MONTHLY-RATE = IN-RATE / 1200
           IF WS-MONTHLY-RATE = 0
               COMPUTE WS-PAYMENT ROUNDED = IN-PRINCIPAL / IN-MONTHS
           ELSE
               COMPUTE WS-FACTOR = (1 + WS-MONTHLY-RATE) ** IN-MONTHS
               COMPUTE WS-PAYMENT ROUNDED =
                   IN-PRINCIPAL * WS-MONTHLY-RATE * WS-FACTOR
                   / (WS-FACTOR - 1)
           END-IF.

       BUILD-SCHEDULE.
           MOVE IN-PRINCIPAL TO WS-BALANCE
           PERFORM VARYING WS-I FROM 1 BY 1 UNTIL WS-I > IN-MONTHS
               COMPUTE WS-INTEREST = WS-BALANCE * WS-MONTHLY-RATE
               IF WS-I = IN-MONTHS
                   MOVE WS-BALANCE TO WS-PRIN-PART
                   COMPUTE WS-PAY-THIS = WS-PRIN-PART + WS-INTEREST
               ELSE
                   COMPUTE WS-PRIN-PART = WS-PAYMENT - WS-INTEREST
                   IF WS-PRIN-PART > WS-BALANCE
                       MOVE WS-BALANCE TO WS-PRIN-PART
                   END-IF
                   COMPUTE WS-PAY-THIS = WS-PRIN-PART + WS-INTEREST
               END-IF
               SUBTRACT WS-PRIN-PART FROM WS-BALANCE
               ADD WS-PAY-THIS TO WS-TOTAL-PAID
               ADD WS-INTEREST TO WS-TOTAL-INTEREST

               MOVE WS-I         TO OD-MONTH
               MOVE WS-PAY-THIS  TO OD-PAYMENT
               MOVE WS-PRIN-PART TO OD-PRINCIPAL
               MOVE WS-INTEREST  TO OD-INTEREST
               MOVE WS-BALANCE   TO OD-BALANCE
               DISPLAY OUT-DETAIL
           END-PERFORM.

       ABORT-WITH-ERROR.
           DISPLAY OUT-ERROR
           MOVE 1 TO RETURN-CODE
           STOP RUN.
