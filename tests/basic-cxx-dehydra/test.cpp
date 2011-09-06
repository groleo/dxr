int n=0;
int k=0;
int horses[500];


static int solve();

namespace TestNameSpace {
	struct declaredStruct ;
	struct baseStruct {
		int dummy;
		enum SOME_ENUM {
			abc
		};
		virtual void V();
		void SS(){
			dummy++;
		}
	} ;
	struct test_struct : public baseStruct {
		int a;
		void test(){}
	};
	typedef struct test_struct test_struct_t ;
};
static int solve()
{
	return 0;
}
int read_input()
{
	int i=0;
	for ( i=0; i<n;++i)
		for ( i=0; i<n;++i)
			solve();
	return 0;
}

int main(int argc, char*argv[])
{
	read_input();
	solve();
}
