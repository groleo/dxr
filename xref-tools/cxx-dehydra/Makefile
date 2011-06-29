prebuild:
	echo "Noting to be made"

can-use:
	@if [ -z "$$(which llvm-config)" -o \
			! -d $$(llvm-config --includedir)/clang ]; then \
		echo "no"; \
	else \
		echo "yes"; \
	fi

clean:
	rm -rf *.o libclang-index-plugin.so
