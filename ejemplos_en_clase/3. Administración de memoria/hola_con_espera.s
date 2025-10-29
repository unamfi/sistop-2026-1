	.file	"hola_con_espera.c"
	.text
	.globl	total
	.data
	.align 4
	.type	total, @object
	.size	total, 4
total:
	.long	5
	.section	.rodata
	.align 8
.LC0:
	.string	"Este es un programa sencillo, trivial, y hasta aburrido"
.LC1:
	.string	"\302\277Qu\303\251 n\303\272mero nos gusta?"
.LC2:
	.string	"%d"
.LC3:
	.string	"%d "
.LC4:
	.string	"\n"
	.text
	.globl	main
	.type	main, @function
main:
.LFB6:
	.cfi_startproc
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	subq	$32, %rsp
	movl	$4, %edi
	call	malloc@PLT
	movq	%rax, -16(%rbp)
	leaq	.LC0(%rip), %rax
	movq	%rax, %rdi
	call	puts@PLT
	leaq	.LC1(%rip), %rax
	movq	%rax, %rdi
	call	puts@PLT
	leaq	-20(%rbp), %rax
	movq	%rax, %rsi
	leaq	.LC2(%rip), %rax
	movq	%rax, %rdi
	movl	$0, %eax
	call	__isoc99_scanf@PLT
	movl	$0, -4(%rbp)
	jmp	.L2
.L3:
	movl	-20(%rbp), %eax
	movl	%eax, %esi
	leaq	.LC3(%rip), %rax
	movq	%rax, %rdi
	movl	$0, %eax
	call	printf@PLT
	addl	$1, -4(%rbp)
.L2:
	movl	total(%rip), %eax
	cmpl	%eax, -4(%rbp)
	jl	.L3
	leaq	.LC4(%rip), %rax
	movq	%rax, %rdi
	call	puts@PLT
	movq	-16(%rbp), %rax
	movq	%rax, %rdi
	call	free@PLT
	movl	$0, %eax
	leave
	.cfi_def_cfa 7, 8
	ret
	.cfi_endproc
.LFE6:
	.size	main, .-main
	.ident	"GCC: (Debian 14.3.0-5) 14.3.0"
	.section	.note.GNU-stack,"",@progbits
