# Changelog

## v2.45.0 (2026-11-09)

### Features

- Group the source file pages under a sources page ([`e713c30`](https://github.com/yanga-project/yanga/commit/e713c30eadf85f86f780199e56b380c41cb856ae))

## v2.44.0 (2026-11-09)

### Features

- Add a generator that runs clang-tidy per source and writes a static analysis report ([`ccfcd70`](https://github.com/yanga-project/yanga/commit/ccfcd703e230118c44790647cbd4ec522d127e21))

## v2.43.0 (2026-11-08)

### Features

- Register reports for the spl overview ([`a8d114c`](https://github.com/yanga-project/yanga/commit/a8d114ceadf71ced54f7b1c3d4c048b28d0f8375))

## v2.42.1 (2026-11-06)

### Bug fixes

- Run the report after the variant is linked ([`60f704b`](https://github.com/yanga-project/yanga/commit/60f704b4bf5724312db250104b6ba1369152b927))

## v2.42.0 (2026-11-04)

### Features

- Add a component test report from the googletest junit results ([`fde10dd`](https://github.com/yanga-project/yanga/commit/fde10dd4468a1eba2eb9a2def8e0b93f61ef0515))

### Bug fixes

- Update pip and certifi for the emsign ca incident and require python 3.11 ([`d4369bc`](https://github.com/yanga-project/yanga/commit/d4369bc23d1fba6d5dbfa6337e197a1f2d100410))

### Documentation

- Move repository to yanga-project organization ([`bbd8afc`](https://github.com/yanga-project/yanga/commit/bbd8afc1d7cd00e651003de7d75a1dc523b06bf0))

## v2.41.1 (2026-10-20)

### Bug fixes

- Create docs target for components with only docs files ([`1d9a451`](https://github.com/yanga-project/yanga/commit/1d9a45121cc5155eaea8d232608b092f58b150b9))

## v2.41.0 (2026-10-19)

### Features

- Generate targets for container and integration components ([`d9d13da`](https://github.com/yanga-project/yanga/commit/d9d13da4f5d037d9557eeb1881816fbd95a7bcf4))

### Bug fixes

- Set zephyr install dirs through the fixture list ([`df5cc35`](https://github.com/yanga-project/yanga/commit/df5cc3566f22d94c62631989b6378e616a670408))

## v2.40.0 (2026-09-19)

### Features

- Add support for zephyr builds ([`19f9c41`](https://github.com/yanga-project/yanga/commit/19f9c41d4d11ba566cdd62ce04d839444a4f51f2))

## v2.39.0 (2026-09-18)

### Features

- Add create shared library generator ([`0c3184a`](https://github.com/yanga-project/yanga/commit/0c3184aaea4be457941eb93ad504687f9412d8c9))

### Bug fixes

- Merge component tracefiles in the variant report ([`08c5584`](https://github.com/yanga-project/yanga/commit/08c5584fc08bab52c6c1ca70a74f811fe24e4529))

## v2.38.0 (2026-09-18)

### Bug fixes

- Link with apple's ld on macos ([`3781480`](https://github.com/yanga-project/yanga/commit/3781480f47b7ce6624e0f775ea81a085273ef5b5))

### Features

- Adopt the dual feature model and update features cli ([`0ceb74f`](https://github.com/yanga-project/yanga/commit/0ceb74fbbcb2854b2ded3ca0d0f2f3930d58cb6a))

## v2.37.1 (2026-09-09)

### Bug fixes

- Header only libraries can not have target link deps ([`93fafbd`](https://github.com/yanga-project/yanga/commit/93fafbd028d9c6938cafefa3538240bc46f34c09))

## v2.37.0 (2026-09-05)

### Features

- Include custom user cmake files ([`3338896`](https://github.com/yanga-project/yanga/commit/3338896b471a33fd3c488ffd88aa16ed7c84f861))

## v2.36.1 (2026-09-04)

### Bug fixes

- Components list are not updated when selecting the platform ([`0d8fab9`](https://github.com/yanga-project/yanga/commit/0d8fab98b6b99bfe9f021e3d17ffbfafd3a042c4))

## v2.36.0 (2026-07-04)

### Features

- Yanga kickstart uses poks and builds on all supported oss ([`26a5b3b`](https://github.com/yanga-project/yanga/commit/26a5b3b35f0aef8a8d86029e694acba6b7810fbe))
- Adopt yanga-core report path constants ([`24b4ec4`](https://github.com/yanga-project/yanga/commit/24b4ec496acf4c6e6745cefafb793dab5a29ea6c))

## v2.35.0 (2026-06-28)

### Features

- Add cli command to view and edit the features ([`2cfe085`](https://github.com/yanga-project/yanga/commit/2cfe085c936cbb935df0218c1a5f1ef4d2d8c013))

## v2.34.0 (2026-06-22)

### Features

- Update component domain naming ([`255ccfd`](https://github.com/yanga-project/yanga/commit/255ccfd6fd0e2c2d1b8e11873ff64deb8283fd89))

## v2.33.0 (2026-06-17)

### Features

- Locate googletest dependency even when using custom versions ([`13f276d`](https://github.com/yanga-project/yanga/commit/13f276dd487ba280dc21c2c295fba44ecd82fd9b))
- Easily debug config failures with tracking items file location ([`d76a203`](https://github.com/yanga-project/yanga/commit/d76a2033f36c4c3d8d3a526e33313c657b9253df))

## v2.32.0 (2026-05-09)

### Bug fixes

- Build files are not regenerated when yanga generators are changed ([`03f02d1`](https://github.com/yanga-project/yanga/commit/03f02d1c1cfde2504a0452cf5b93f9010c0b8344))

### Features

- Add component clean target to gui ([`eb0705e`](https://github.com/yanga-project/yanga/commit/eb0705e5af6b26571f2b3db84c333803ffcf2f90))

## v2.31.0 (2026-05-09)

### Features

- Add run pristine option ([`a8e072d`](https://github.com/yanga-project/yanga/commit/a8e072dc67dbb1eb38b0acac024f4e1e0d270352))
- Add component clean target ([`fb05938`](https://github.com/yanga-project/yanga/commit/fb059389ba03a61f8c5bb86aec035fdfc52c1fc4))
- Make sure clean command handles unknown artifacts without failing ([`ad6a515`](https://github.com/yanga-project/yanga/commit/ad6a5158f64e36be867b47b0efebe4d3a89999c2))

### Bug fixes

- Tk gui freezes and no terminal output ([`59c136b`](https://github.com/yanga-project/yanga/commit/59c136b2813032e5bc3be1be7470b4985e93abde))
- Component clean target is failing ([`7e9aa13`](https://github.com/yanga-project/yanga/commit/7e9aa130b9f7ed14c369ea9694aeaf69b4ea7649))

## v2.30.1 (2026-05-01)

### Bug fixes

- Relative project paths are not normalized ([`252019c`](https://github.com/yanga-project/yanga/commit/252019cf8544d9cc8f02da9fdc5e69a60e5edcc7))
- Clean target fails for the gtest because of the coverage extra files ([`87a2d4a`](https://github.com/yanga-project/yanga/commit/87a2d4aff1f6130f0ff8ba97641af0325b013121))

## v2.30.0 (2026-04-26)

### Features

- Add info command ([`27bf86b`](https://github.com/yanga-project/yanga/commit/27bf86b0889999b924aca2e1edd592f1c3b5b650))

## v2.29.1 (2026-03-21)

### Bug fixes

- Coverage report component objects option is wrongly expanded ([`287c720`](https://github.com/yanga-project/yanga/commit/287c72025bf9e2c4148ea1b829c7c5fecf11df79))

## v2.29.0 (2026-03-11)

### Features

- Move yanga core to a separate package ([`2714015`](https://github.com/yanga-project/yanga/commit/271401517ea7115b353630b7bd6028942a961f03))

## v2.28.0 (2026-02-17)

### Bug fixes

- Parsing west manifest expects wrong content ([`5e8f741`](https://github.com/yanga-project/yanga/commit/5e8f741102f593f74cc0e58f8b9a7b4bf3d9bcf2))
- Cmake strings not quoted properly ([`1738334`](https://github.com/yanga-project/yanga/commit/173833487b7f73cf8cfa767a9681321c10823345))
- Wrong west configuration in kickstart ([`d24e60b`](https://github.com/yanga-project/yanga/commit/d24e60b7bb70b0e84a0a046ac4de3d85dd5262a0))

### Features

- Add poks install step ([`bbd9682`](https://github.com/yanga-project/yanga/commit/bbd968271822f97b8c66adeff713af6b5da2d06b))

### Documentation

- Restructure based on diataxis framework ([`11f07f0`](https://github.com/yanga-project/yanga/commit/11f07f065fe88fbb66f3178724bcd433c8caf1ac))

## v2.27.4 (2026-02-08)

### Bug fixes

- West clone depth attribute is ignored ([`819e2d2`](https://github.com/yanga-project/yanga/commit/819e2d2341fcb9a5cdd6ad2cc0a74d1800df8072))

## v2.27.3 (2026-02-05)

### Bug fixes

- Kickstart platform name is not correct ([`6c6b25d`](https://github.com/yanga-project/yanga/commit/6c6b25dad6216bca7c17c3681c85681c0dcda220))

## v2.27.2 (2026-02-03)

### Bug fixes

- Wrong kickstart boostrap path ([`d3f6509`](https://github.com/yanga-project/yanga/commit/d3f650914ab3aaa8f5194f6863f29e1d6b551ab6))

## v2.27.1 (2026-01-18)

### Bug fixes

- Cli crashes on dev containers without gui support (tkinter) ([`57575b3`](https://github.com/yanga-project/yanga/commit/57575b3265146e77ce20176106be30588d3f138e))

## v2.27.0 (2026-01-17)

### Features

- Scoop install step only enabled on windows ([`e375d71`](https://github.com/yanga-project/yanga/commit/e375d71443636f906c2dbdcb105253c76abbeaf0))

## v2.26.0 (2026-01-15)

### Features

- Update bootstrap for kickstart projects ([`96e6469`](https://github.com/yanga-project/yanga/commit/96e6469857fbf4f6266bad733b9cf6be8aa10d5a))

### Bug fixes

- Does not handle subprocess flag for windows shell ([`9377aa5`](https://github.com/yanga-project/yanga/commit/9377aa5b4694243890279c802481f7f664af4f01))

## v2.25.1 (2025-10-25)

### Bug fixes

- Targets report does not show dependencies to executable sources ([`e38b35f`](https://github.com/yanga-project/yanga/commit/e38b35fe971b05a70ef6de81b51ca3f6768a1d9a))

## v2.25.0 (2025-10-25)

### Features

- Refactor targets dependencies report and improve browse experience ([`d132555`](https://github.com/yanga-project/yanga/commit/d1325551211cfc3e75ed1226e389b443146e2adf))

## v2.24.0 (2025-10-24)

### Bug fixes

- Component variant coverage path is wrong ([`67a8b9e`](https://github.com/yanga-project/yanga/commit/67a8b9e7d2932fb18d9703542cc4ea691e5b3c8b))

### Documentation

- Update concepts chapter ([`41e453c`](https://github.com/yanga-project/yanga/commit/41e453c8d0c821d69f9f7dc80d26fa278e63bcbe))

### Features

- Refactor the coverage reports to avoid using obsolete .md files ([`6559acc`](https://github.com/yanga-project/yanga/commit/6559acc9f04bf56fa9ca7f23a1cb9444a9c92df9))

## v2.23.2 (2025-10-21)

### Bug fixes

- Missing changelog template ([`c19f2cc`](https://github.com/yanga-project/yanga/commit/c19f2ccbb4949bd7e690280e9258e39b0fd778dc))

## v2.23.1 (2025-10-21)

### Bug fixes

- Semantic release does not update changelog ([`0aa75dd`](https://github.com/yanga-project/yanga/commit/0aa75dd870461ba5f397346ce078608d323022ea))

## v2.23.0 (2025-10-20)

### Features

- Default to first platform build type if none selected ([`c074f23`](https://github.com/yanga-project/yanga/commit/c074f2379dae38ae9c8256b8e0be44d8ab41d155))

## v2.22.1 (2025-10-19)

### Bug fixes

- Links to generated html files work only from the main page ([`a159b31`](https://github.com/yanga-project/yanga/commit/a159b31d654e6237b896afab73c0633e030e03da))

## v2.22.0 (2025-10-19)

### Features

- Refactor targets data as separate generator ([`d9627a8`](https://github.com/yanga-project/yanga/commit/d9627a858b4497cdf7387b0a9083a9adbd22eb85))
- Add objects dependencies report cmake generator ([`132da50`](https://github.com/yanga-project/yanga/commit/132da50101f044e2cf22c310052db397a961fd7a))
- Add support for including generated html in the report ([`85d8063`](https://github.com/yanga-project/yanga/commit/85d806378f71cbf23d83c0ee292abbaec52d17b9))

## v2.21.0 (2025-10-18)

### Features

- Use shorter cli argument names ([`bd0ec55`](https://github.com/yanga-project/yanga/commit/bd0ec556374bbb0efb7b085d5a2291670c6c231a))
- Relax required components search to support implicit header components ([`405da99`](https://github.com/yanga-project/yanga/commit/405da992362df41babe492102c3044e7f59636f6))
- Fail if components circular dependencies are found ([`cfedb25`](https://github.com/yanga-project/yanga/commit/cfedb25f78548f1ff3cc79e88550a5d348014f48))
- Add component aliases support ([`d3a0ab6`](https://github.com/yanga-project/yanga/commit/d3a0ab6fb745a5b8cddc8648be9408b47d5f0bbb))

## v2.20.0 (2025-10-16)

### Features

- Add support for none build type ([`cd96251`](https://github.com/yanga-project/yanga/commit/cd9625162eebe5d557a030b8592e228bfbefa6d5))
- Interactively ask user for the build type ([`71c3333`](https://github.com/yanga-project/yanga/commit/71c3333ebb07fbf078e5e5a186b4ea3ef6f94717))
- Use subdirectory to group all external dependencies ([`b47d621`](https://github.com/yanga-project/yanga/commit/b47d621096bd3a553c660ccc73f30a6b4069cafc))

### Bug fixes

- Variant compile target is missing ([`fea573d`](https://github.com/yanga-project/yanga/commit/fea573d0358b9f5e8a8c91159fb58c9ada52f6f4))
- Components selection not directly visible in gui ([`93bc140`](https://github.com/yanga-project/yanga/commit/93bc140b4ef7c4290dca9b58721cd80c0d5d22f8))
- Handle platforms with no build type in vs code ([`645e9cd`](https://github.com/yanga-project/yanga/commit/645e9cdc88304e7b5fb70c9309a3c898b0c4727c))

## v2.19.0 (2025-09-25)

### Features

- Add variant platform specific west dependencies ([`01c7f72`](https://github.com/yanga-project/yanga/commit/01c7f7231f7e45eb2f9e336e0d7472f3e32cb153))
- Support platform specific components ([`eeba813`](https://github.com/yanga-project/yanga/commit/eeba81323e5fb2ed3475c99cf76233d14fa2012c))
- Add support for header only libraries ([`cbb2f87`](https://github.com/yanga-project/yanga/commit/cbb2f873c126c93e48aeaf599a00be7f8ee36f9f))
- Define build targets for platforms and show in gui ([`793de58`](https://github.com/yanga-project/yanga/commit/793de58c541112614a9f3140537d384edb901180))

## v2.18.0 (2025-09-24)

### Features

- Add support for integration tests components docs ([`4db8d70`](https://github.com/yanga-project/yanga/commit/4db8d709d160d60cb7f793c91f40ef7de50657c8))

### Bug fixes

- Component mocking config is ignored ([`e7b5502`](https://github.com/yanga-project/yanga/commit/e7b550281b62ee0eed2e5f879d64713fb4c99d72))

## v2.17.1 (2025-09-21)

### Bug fixes

- Gtest productive code library fails for multiple objects ([`9eba01b`](https://github.com/yanga-project/yanga/commit/9eba01bfb19c927c112af62f65c3ed5db3cbbe1e))

## v2.17.0 (2025-09-21)

### Features

- Support cmake post build custom commands ([`1a74538`](https://github.com/yanga-project/yanga/commit/1a74538da666020d92cd85a875c482cad24282a0))

### Bug fixes

- No platform files are initialized by kickstart ([`beb6082`](https://github.com/yanga-project/yanga/commit/beb6082b75f7f253959aa6b8180e565eb2afa88a))

## v2.16.0 (2025-09-17)

### Features

- Add option to only kickstart the build environment ([`62a2204`](https://github.com/yanga-project/yanga/commit/62a220486461a1f6b87eb70ab90ecfc7b18eb5d1))

## v2.15.0 (2025-09-16)

### Features

- Update cppcheck report to show file chapters ([`11e1ddb`](https://github.com/yanga-project/yanga/commit/11e1ddb2117c54cdf017ab0fbcf79a475d0c3ed3))

## v2.14.1 (2025-09-16)

### Bug fixes

- Build fails if the project directory is not absolute ([`baa8397`](https://github.com/yanga-project/yanga/commit/baa83972a2365f15ec2a5ec05e8814095edfabd5))

## v2.14.0 (2025-09-14)

### Features

- Generate vs code cmake tools project files ([`42e5486`](https://github.com/yanga-project/yanga/commit/42e548601bac7c78245fcaf8aef9a2620424d2eb))
- Add not interactive mode ([`e1dacaa`](https://github.com/yanga-project/yanga/commit/e1dacaac17b8137e1762849668e306acdced0604))

### Bug fixes

- Variant build dir used when no variable is set ([`216feb3`](https://github.com/yanga-project/yanga/commit/216feb3e4eb4612ed1a61771f2655cece9ff1921))

## v2.13.0 (2025-09-14)

### Features

- Add variant platform specific components and configuration ([`dd55825`](https://github.com/yanga-project/yanga/commit/dd5582599369cdf32cb723c3a75beb2a47dceb8e))
- Assign components directly to variants ([`ccb0262`](https://github.com/yanga-project/yanga/commit/ccb02629184da13ee2c84fedca97a3b1275a1812))
- Create .yanga build dir ([`2559f0a`](https://github.com/yanga-project/yanga/commit/2559f0a6fea755be72d8f54bb672a27014cc08b0))

## v2.12.0 (2025-09-14)

### Features

- Add platform and variant specific scoop dependencies ([`b33bd5f`](https://github.com/yanga-project/yanga/commit/b33bd5f5df3af1760ffed559b27459499f574fc7))

### Bug fixes

- View gui freezes if columns are deselected and refresh multiple times ([`e47e05d`](https://github.com/yanga-project/yanga/commit/e47e05d4783a9748dd770ce8c82ab2c5ed023a96))

## v2.11.0 (2025-09-13)

### Features

- Add feature configuration view command ([`9c71932`](https://github.com/yanga-project/yanga/commit/9c7193215b9c05fff0add65e6d009b4433085854))
- Add the feature configuration to the report data ([`398e074`](https://github.com/yanga-project/yanga/commit/398e074d5cd482bae2cdee2970e305815e3b1580))
- Generate kconfig features documentation ([`ce62861`](https://github.com/yanga-project/yanga/commit/ce62861a0e66ee228b86d31b00609dc0736c79ae))
- Generate myst markdown flavour for sources ([`f173f7c`](https://github.com/yanga-project/yanga/commit/f173f7c6d88086c58e92e2581fe3f998672d46cb))

### Bug fixes

- Cppcheck documentation generate warnings with invalid c snippet ([`be063e8`](https://github.com/yanga-project/yanga/commit/be063e84d0e0c43e4b2960eff27946bfc0ad66da))
- Components coverage reports are missing in the variant report ([`cc61291`](https://github.com/yanga-project/yanga/commit/cc6129171df9f57833ed2bb770e7d5735e9a207a))
- Test sources docs not generated because no test results are registered ([`6e3f924`](https://github.com/yanga-project/yanga/commit/6e3f9243b2a96c0b701353c49906e8fa4d432374))
- Test files docs are generated even if not relevant for platform ([`14069c7`](https://github.com/yanga-project/yanga/commit/14069c715e1bdecd1ae9ceffc94c725a697c3ae8))
- Reports dependency is missing ([`2b57931`](https://github.com/yanga-project/yanga/commit/2b57931642f6a4c2c274a7cbc1a0d257c25c9cbc))
- Cppcheck code block is not in myst-parser format ([`60218ef`](https://github.com/yanga-project/yanga/commit/60218efd7728da4671bafeeb2cc93ba1b64c38f2))
- Coverage data is empty when components sources have subfolders ([`441d752`](https://github.com/yanga-project/yanga/commit/441d752dcbb3731c77d397b9a4ee9c62edb96507))
- Component object library is not created if not testable ([`9f0ea35`](https://github.com/yanga-project/yanga/commit/9f0ea352e06ed65410c101c873fab7e045fdd3f0))

## v2.10.0 (2025-09-06)

### Features

- Generate targets dependencies docs ([`83c5f3b`](https://github.com/yanga-project/yanga/commit/83c5f3b3b4155e6a07e88571c3f242b49ce3ad6d))
- Generate build targets data ([`42e401f`](https://github.com/yanga-project/yanga/commit/42e401f0c7e0746b44568546f527b1be8dced21a))
- Not testable components can be compiled and lint ([`12cbc0d`](https://github.com/yanga-project/yanga/commit/12cbc0d6d540e37a14dd2f6cdef0520d83b6afa1))
- Create variant coverage report ([`ad8fc78`](https://github.com/yanga-project/yanga/commit/ad8fc788e05365c7b232c652bf0ff0dbbb28e0de))
- Add coverage to component report ([`8a9aac7`](https://github.com/yanga-project/yanga/commit/8a9aac70b47d90ef6104a3332fd8e80614ec19c9))

## v2.9.0 (2025-09-02)

### Features

- Add component report generation ([`65410da`](https://github.com/yanga-project/yanga/commit/65410dac709f7affdc88d6e0bb770140cf662376))
- Generate component sources documentation ([`7eb6623`](https://github.com/yanga-project/yanga/commit/7eb6623c7550adcc764080b17725d3c4af9f2691))
- Generate component coverage html report ([`a1df5b3`](https://github.com/yanga-project/yanga/commit/a1df5b3525b9998f71912f81d6feb6754211bcb8))
- Add component gcovr configuration generation ([`5047cb1`](https://github.com/yanga-project/yanga/commit/5047cb1a0494693b54edf6968b29236d8fb4a379))
- Generate component specific docs config file ([`702be62`](https://github.com/yanga-project/yanga/commit/702be62c01b695b351dc237d0856d0616dbd65a1))
- Add reports cmake generator ([`4bd9680`](https://github.com/yanga-project/yanga/commit/4bd96807987776f29657253036889d43070b0abf))
- Add cppcheck report generator ([`2d0be13`](https://github.com/yanga-project/yanga/commit/2d0be13e2ebe5285bc31a62817a7473b388d7d7d))
- Add cppcheck generator to generate component xml report ([`9f5ddfd`](https://github.com/yanga-project/yanga/commit/9f5ddfdc29892dcdb9ef08e8230b5fa6f7542535))
- Add compile commands filter command ([`829f5d9`](https://github.com/yanga-project/yanga/commit/829f5d903e7c6dd26066878f134e25cbeafdbe4d))

### Bug fixes

- Execution context environment is not provided to subprocesses ([`1ce7133`](https://github.com/yanga-project/yanga/commit/1ce71331a5cd76bf65fa8ace18e76b144553c170))

## v2.8.0 (2025-08-24)

### Features

- Add user mocking configuration ([`a91708b`](https://github.com/yanga-project/yanga/commit/a91708b60af7505e9b9544abe14b9bb34dc566de))

## v2.7.0 (2025-08-24)

### Features

- Generate variant cmake configuration file ([`802dcc7`](https://github.com/yanga-project/yanga/commit/802dcc716cdba8dbf0425fb4af38d154356d44d3))
- Group generated component build artifacts ([`98bcf28`](https://github.com/yanga-project/yanga/commit/98bcf28fde8bfaddb5474f9a9b625e79475b8d4a))
- Use clanguru for mocking ([`fe83d18`](https://github.com/yanga-project/yanga/commit/fe83d187f62a0d2b2ff47befafc8e0bad356f974))
- Add platform and variant specific external dependencies ([`dd7921c`](https://github.com/yanga-project/yanga/commit/dd7921c10399082d78f4d03196f869bab5d93759))
- Use project root cmake file ([`5a69ada`](https://github.com/yanga-project/yanga/commit/5a69ada4cc53a67630ed63890ec78758e3139181))

## v2.6.0 (2025-08-08)

### Features

- Collect component specific includes ([`4ad2879`](https://github.com/yanga-project/yanga/commit/4ad2879c97b8cde07ab7bdfba487b94253559ceb))
- Add use global includes configuration switch ([`2b82e83`](https://github.com/yanga-project/yanga/commit/2b82e83a91c43441230d4bfd73f43c87c798af6b))
- Add component includes resolver ([`6c26d60`](https://github.com/yanga-project/yanga/commit/6c26d60ca7e7936eed55005d09f9fcc63d3fb8d2))
- Add support for build type ([`5472db4`](https://github.com/yanga-project/yanga/commit/5472db40fa06d86c5efa2131e679c2159e8b8007))

## v2.5.0 (2025-06-05)

### Features

- Use pypeline internal bootstrap ([`64153b5`](https://github.com/yanga-project/yanga/commit/64153b513be284740f1be044ff1052b6432eab33))

## v2.4.1 (2025-06-02)

### Bug fixes

- Kickstarter files are missing in the installation ([`cd53182`](https://github.com/yanga-project/yanga/commit/cd531825d053237ea159256c37edcc2afc3111f7))

## v2.4.0 (2025-05-13)

### Features

- Add generate setup scripts for kickstarter ([`2da32b0`](https://github.com/yanga-project/yanga/commit/2da32b0a5f4b0085cc4278b41d291f34b199a090))

## v2.3.0 (2025-02-07)

### Features

- Update bootstrap and refactor init command ([`dbd59ba`](https://github.com/yanga-project/yanga/commit/dbd59ba1df7ee1d09a10d49e874f5d27cfafa9eb))

### Bug fixes

- Component junit contains tests from other components ([`7112082`](https://github.com/yanga-project/yanga/commit/7112082875e5f60d243053fa7247b7e65a40ac42))

## v2.2.2 (2025-02-05)

### Bug fixes

- Example project cmake file include fails ([`1fef006`](https://github.com/yanga-project/yanga/commit/1fef006f008b178d2ce8a3fd2e50fdc9eaffde01))

## v2.2.1 (2025-02-03)

### Bug fixes

- Missing dependency for creating windows executable ([`2dedee2`](https://github.com/yanga-project/yanga/commit/2dedee225b06fa3368919b623a01ad984a945279))

## v2.2.0 (2025-02-03)

### Features

- Make automocking feature configurable ([`aa67e13`](https://github.com/yanga-project/yanga/commit/aa67e13c7e401486e9ad778ad24eae4b08dca214))

## v2.1.1 (2025-02-03)

### Bug fixes

- Yanga projects fail to be installed as packages in venv ([`28da64c`](https://github.com/yanga-project/yanga/commit/28da64cbb3fe10bb61b2f89f493a347ed9b20b59))

## v2.1.0 (2024-09-29)

### Features

- Support user specific configuration files ([`1c0a711`](https://github.com/yanga-project/yanga/commit/1c0a711c1838fc3627d2b601450d3ff3c3bff703))

## v2.0.0 (2024-09-29)

### Features

- Migrate to pypeline steps ([`ce65cc3`](https://github.com/yanga-project/yanga/commit/ce65cc3b8ca56bf0ce74e632af26fa989909068d))

## v1.7.0 (2024-04-28)

### Features

- Integrate auto mocking for gtest ([`8b8540b`](https://github.com/yanga-project/yanga/commit/8b8540b262e5394612eb8bed7fcbacc847b49148))

### Bug fixes

- Missing dependencies for autocompletion ([`a8f24ce`](https://github.com/yanga-project/yanga/commit/a8f24ce7730f5b4091436bdadeacaa3a1a5c6bbf))

## v1.6.0 (2024-03-29)

### Features

- Use typer for handling command line ([`3cbd5c8`](https://github.com/yanga-project/yanga/commit/3cbd5c840261414851fabacf467cdb506b9860f8))

## v1.5.9 (2024-03-26)

### Bug fixes

- Path to pip configuration file is wrong ([`25d6ac3`](https://github.com/yanga-project/yanga/commit/25d6ac3f15f4842fe4b35c5d7e9e175685501b1b))
- Bootstrap python fails because of lessmsi ([`ccf194b`](https://github.com/yanga-project/yanga/commit/ccf194b16909c684990b1db74702ee79d429bdb0))

## v1.5.8 (2024-03-11)

### Bug fixes

- Pypi release is broken ([`d4b37d8`](https://github.com/yanga-project/yanga/commit/d4b37d8444266947e723ab63c30779f0e38d58bf))

## v1.5.7 (2024-03-10)

### Bug fixes

- Readthedocs build fails ([`38e1e7d`](https://github.com/yanga-project/yanga/commit/38e1e7d190987bbab1dbe30300a0a0a0b9841a7f))

## v1.5.6 (2024-03-10)

### Documentation

- Change to .md and cleanup ([`d029141`](https://github.com/yanga-project/yanga/commit/d0291412f691e1de9fdbde29c5ced7a06b70923b))

### Bug fixes

- Bootstrap pip.ini path is not correct ([`2169397`](https://github.com/yanga-project/yanga/commit/2169397507953a4a101e6b7f15439a14e1792106))

## v1.5.5 (2024-02-26)

### Bug fixes

- Scoop install step can not create file ([`1b1cd5e`](https://github.com/yanga-project/yanga/commit/1b1cd5ef6c249227ada3e83472e6bbc51be48fca))

## v1.5.4 (2024-02-26)

### Bug fixes

- Cmake builder fails to load generator ([`1bc68ee`](https://github.com/yanga-project/yanga/commit/1bc68eef31800b4348c51e0c07c40798a49a6afa))

## v1.5.3 (2024-02-26)

### Bug fixes

- Generated project does no install latest yanga version ([`e22e9f2`](https://github.com/yanga-project/yanga/commit/e22e9f23decf60d614ca1cf94a8ab268f833f88c))

## v1.5.2 (2024-02-26)

### Bug fixes

- Yanga standalone exe not working with cmake generators ([`3429bde`](https://github.com/yanga-project/yanga/commit/3429bde982fb27eb3bb2a38b724d25ab38457b1d))

## v1.5.1 (2024-02-25)

### Bug fixes

- Cmake generators loader can not find generator ([`3d68968`](https://github.com/yanga-project/yanga/commit/3d6896822e0f3f5341c223e9f4c5b0bb8e766e4a))

## v1.5.0 (2024-02-25)

### Features

- Update mini project for vscode cmake extension ([`78614f3`](https://github.com/yanga-project/yanga/commit/78614f377706d5f833517a6a461597b1e47b8d2c))
- Update gui to support platforms ([`327652d`](https://github.com/yanga-project/yanga/commit/327652d6065c940fccdca76e897cbd320252a939))
- Dynamically load cmake generators ([`000c96f`](https://github.com/yanga-project/yanga/commit/000c96f5a32695d929c36aaaab2e7142ea331e35))
- Variant config location is flexible ([`14bcc07`](https://github.com/yanga-project/yanga/commit/14bcc07e662c9820b5aaa2f409b1546f28abd88e))

## v1.4.0 (2024-02-24)

### Features

- Component files location is flexible ([`28e2c1d`](https://github.com/yanga-project/yanga/commit/28e2c1defea3a7d9f46ef239444fb0c65fafac7f))

## v1.3.0 (2024-02-24)

### Features

- Add support for platform toolchain file ([`6c4ff60`](https://github.com/yanga-project/yanga/commit/6c4ff60de13a6c5c1f77f77851f879c36f9d750f))

## v1.2.1 (2024-02-24)

### Bug fixes

- Standalone exe causes antivirus false positive ([`d55bfdd`](https://github.com/yanga-project/yanga/commit/d55bfdd6112119ad473131abceb8643871fbb18b))

## v1.2.0 (2024-02-24)

### Features

- Make variant optional ([`883097c`](https://github.com/yanga-project/yanga/commit/883097cb2e0da0b74bece4cd2ebae8d21655ee04))

## v1.1.0 (2024-02-24)

### Features

- Print project info when refreshing gui ([`8746958`](https://github.com/yanga-project/yanga/commit/8746958a549d32bdb68e54924e0af0a3e3be1818))

## v1.0.1 (2024-02-24)

### Bug fixes

- Pipeline steps are not loaded in the exe ([`fd65cd5`](https://github.com/yanga-project/yanga/commit/fd65cd5dd303bc1ee21f013858b4b0c243e60bcf))

## v1.0.0 (2024-02-23)

### Bug fixes

- Coverage job error when using subprocess ([`6087267`](https://github.com/yanga-project/yanga/commit/6087267073df228b603eaa086be93039ccbc84f8))
- Only build executable for tagged commits ([`9f924e9`](https://github.com/yanga-project/yanga/commit/9f924e9fc9e66f7ec52bbe780f188bff6a9929f0))

### Features

- Replace build command with run ([`0969fb0`](https://github.com/yanga-project/yanga/commit/0969fb0487e61b2f7c378c2bdf2d460008530df1))
- Run single steps and support force run ([`54a3b22`](https://github.com/yanga-project/yanga/commit/54a3b2206dc88006970f678e881f1910d84e5b59))
- Implement run step command ([`1870150`](https://github.com/yanga-project/yanga/commit/187015000e154a061e34de19de3a0e03f5cdeb47))

## v0.26.0 (2024-02-17)

### Bug fixes

- Pytest coverage report generation fails ([`ff76f98`](https://github.com/yanga-project/yanga/commit/ff76f98d40c5881ba657b8e2f44b4e2763240448))
- Bootstrap not running when deps changed ([`5b9f022`](https://github.com/yanga-project/yanga/commit/5b9f02274fbfecad8c32de770c78e457d876f241))

### Features

- Add debug options for test executable ([`3a3dea3`](https://github.com/yanga-project/yanga/commit/3a3dea30cc2278db4dcf872fc192cbd7ab0e232a))

## v0.25.0 (2024-02-14)

### Features

- Add vscode cmake support for mini project ([`0a35dca`](https://github.com/yanga-project/yanga/commit/0a35dca19adc705017379ed5c527e575da15de95))

## v0.24.0 (2024-02-14)

### Features

- Bootstrap support pip trusted host ([`ab6714c`](https://github.com/yanga-project/yanga/commit/ab6714c50c779aca74128b40aa34a29534631883))

## v0.23.0 (2024-02-14)

### Features

- Make python scoop install configurable ([`f824587`](https://github.com/yanga-project/yanga/commit/f82458776851d44724f8887398b692e5a28942f6))

## v0.22.0 (2024-02-13)

### Features

- Add icon to windows executable ([`ad6c8ab`](https://github.com/yanga-project/yanga/commit/ad6c8abd0bc1a588b9c7b21d0b1edb02886b557f))

## v0.21.7 (2024-02-13)

### Bug fixes

- Release windows executable requires a tag ([`5cbc3f2`](https://github.com/yanga-project/yanga/commit/5cbc3f23aa47e46ae6eaf5e12dc5574926f5f837))

## v0.21.6 (2024-02-13)

### Bug fixes

- Release windows executable requires a tag name ([`889d70f`](https://github.com/yanga-project/yanga/commit/889d70fc470a0c74c6b305959ba74876842479d2))

## v0.21.5 (2024-02-13)

### Bug fixes

- Windows executable still not released ([`cde9cf2`](https://github.com/yanga-project/yanga/commit/cde9cf286d35f11c850b69573b110de33e5ce9df))

## v0.21.4 (2024-02-13)

### Bug fixes

- Windows executable release is not triggered ([`97be7dd`](https://github.com/yanga-project/yanga/commit/97be7dd18feb626c1d1e4bbd26ea59166e10ea61))

## v0.21.3 (2024-02-13)

### Bug fixes

- Windows executable name does not contain tag ([`96ef7e1`](https://github.com/yanga-project/yanga/commit/96ef7e119f5a7fad0bbc10920ca50d60fd44013c))

## v0.21.2 (2024-02-13)

### Bug fixes

- Windows executable is not released ([`1b3122e`](https://github.com/yanga-project/yanga/commit/1b3122ef5975f5a1f39c9ed019d400b286402804))

## v0.21.1 (2024-02-11)

### Bug fixes

- Pyinstaller build github action failed ([`2e4e6d5`](https://github.com/yanga-project/yanga/commit/2e4e6d51930d793ea7cec4beae4ba8e6760255ff))

## v0.21.0 (2024-02-11)

### Features

- Create windows executable ([`1ac3625`](https://github.com/yanga-project/yanga/commit/1ac36257b7d578e98b60e4d719f7e9b90ce1b027))

## v0.20.0 (2024-01-31)

### Features

- Bootstrap creates pip.ini for pypi source ([`d4b54e7`](https://github.com/yanga-project/yanga/commit/d4b54e79e63fb01106e07b7067cc6c9bd53d9320))

## v0.19.0 (2024-01-31)

### Bug fixes

- Some bootsrap dependencies are missing ([`37aa08b`](https://github.com/yanga-project/yanga/commit/37aa08b9884c45641beacce7bc8c934d30055132))

### Features

- Read bootstrap config from json ([`ed6b688`](https://github.com/yanga-project/yanga/commit/ed6b688f78d8febc0e35e7c0cb0fd97246b44bf0))

## v0.18.1 (2024-01-22)

### Bug fixes

- Py-app-dev version is not compatible ([`1d52931`](https://github.com/yanga-project/yanga/commit/1d52931d039bd1c435b901f6ba588e62b24909f1))

## v0.18.0 (2024-01-10)

### Features

- Add support for loading installed stages ([`d2a941e`](https://github.com/yanga-project/yanga/commit/d2a941e83f322f4782cc6b7922222ace558e55f2))

## v0.17.1 (2024-01-10)

### Bug fixes

- Gui command help message is incorrect ([`91b7784`](https://github.com/yanga-project/yanga/commit/91b778418a6c07da1c36af1f596a760d0d836575))

## v0.17.0 (2023-12-22)

### Features

- Make mini project default for init ([`982f494`](https://github.com/yanga-project/yanga/commit/982f494afbc3702b55d69ceadb2d0d73ef3fd523))
- Add custom build request for cli ([`1316177`](https://github.com/yanga-project/yanga/commit/1316177a410dda603e6ace655ee9d6a471ab172e))
- Add variant selection in command line ([`c117cfa`](https://github.com/yanga-project/yanga/commit/c117cfa4fc16916af8ebdb6d6c8df8dedba07301))

## v0.16.0 (2023-12-17)

### Features

- Add gtest example to mini project ([`ad4c622`](https://github.com/yanga-project/yanga/commit/ad4c62253782acdb148c84b015618453adb31ef0))

## v0.15.0 (2023-12-17)

### Features

- Integrate unit testing with gtest ([`caa9300`](https://github.com/yanga-project/yanga/commit/caa9300aa9f85231fcff0a2414374f375de2130b))

## v0.14.0 (2023-12-09)

### Features

- Add open in vscode button ([`16b4228`](https://github.com/yanga-project/yanga/commit/16b422855dcfa82a0069920f00999f509e21920e))
- Install gtest with west ([`c8e31fc`](https://github.com/yanga-project/yanga/commit/c8e31fc18c2d0f5f4799f74b53ae63d8ff7874fa))

### Bug fixes

- Missing abstract method decorator ([`272a4cd`](https://github.com/yanga-project/yanga/commit/272a4cd667c763a08312b06a0c43e277631d5a58))

## v0.13.0 (2023-12-03)

### Features

- Implement component compile target ([`4336fcb`](https://github.com/yanga-project/yanga/commit/4336fcbaa3be1f5fe93f2c023d40ca6af6b41046))

## v0.12.0 (2023-11-26)

### Features

- Propagate install dirs in the environment ([`f814a0f`](https://github.com/yanga-project/yanga/commit/f814a0f664939d1c65caa78ea681cca69c827f46))
- Exclude directories from config search ([`44abdae`](https://github.com/yanga-project/yanga/commit/44abdaebcae6490f687ef656e8b0c040e2be2db6))
- Integrate kconfig generation ([`1f0bc8e`](https://github.com/yanga-project/yanga/commit/1f0bc8e54938f6a03506268dc0633808cfa8ffbf))

## v0.11.1 (2023-11-02)

### Bug fixes

- Bootstrap automatically calls yanga ([`3168a58`](https://github.com/yanga-project/yanga/commit/3168a58fb4ce5dd1d8fdb96614a756dce18ec5f7))
- Scoop installer prompts to open tmp file ([`c4bfab3`](https://github.com/yanga-project/yanga/commit/c4bfab3cda594b163868034816cc8924f025f8dd))

## v0.11.0 (2023-11-02)

### Features

- Add option to init bootstrap files ([`9d8fc84`](https://github.com/yanga-project/yanga/commit/9d8fc84b24f878ef3f7932517e8db52fdaace248))

### Bug fixes

- Gui icons dependencies missing ([`be38650`](https://github.com/yanga-project/yanga/commit/be38650b570258381f7d7a3030bd2fa3533a679c))

## v0.10.0 (2023-10-25)

### Bug fixes

- Print subprocess output in realtime ([`10cf353`](https://github.com/yanga-project/yanga/commit/10cf353265413db08176ae228fcae9a3cfa57f34))
- Yanga build only depends on configure ([`a91f18c`](https://github.com/yanga-project/yanga/commit/a91f18cd52a41e03f60f968a7b93d62712a8dec5))

### Features

- Gui handle user exception during build ([`5e17d52`](https://github.com/yanga-project/yanga/commit/5e17d52dbb2c191305f7665cf015697270828fbf))

## v0.9.0 (2023-10-23)

### Bug fixes

- Integration tests for python 3.10 ([`8cbe239`](https://github.com/yanga-project/yanga/commit/8cbe2397c827f3971a4173bbf987f073c0ef8826))
- Build stage fails while writing file ([`344a4ad`](https://github.com/yanga-project/yanga/commit/344a4adc37372106b9b035d65a36659091c5a6b3))
- Variant bom components are ignored ([`2c38f52`](https://github.com/yanga-project/yanga/commit/2c38f52a9068f5818b956f16312b8d96a40a9a58))

### Features

- Create template for minimal yanga project ([`84b3ff6`](https://github.com/yanga-project/yanga/commit/84b3ff61264fbd49f1250514fe806479f81c6530))
- Add cmake build stage ([`0615305`](https://github.com/yanga-project/yanga/commit/06153051c6e0905efb63ea84ff48b5447553360d))
- Add build configure stage ([`9463a2c`](https://github.com/yanga-project/yanga/commit/9463a2cf69fb956bb511908cfe013d95e2d22fda))

## v0.8.2 (2023-10-21)

### Bug fixes

- Project root user config not found ([`a088190`](https://github.com/yanga-project/yanga/commit/a088190f915d956b34d15f52c20566a49805771b))

### Documentation

- Clean up ([`6a82bab`](https://github.com/yanga-project/yanga/commit/6a82babe51d8036f1d06900d31cf3b5e90bfda58))
- Use dark mode ([`8386089`](https://github.com/yanga-project/yanga/commit/8386089f3cb788753d0759d7a503e6550227b6b2))

## v0.8.1 (2023-09-30)

### Bug fixes

- Scoop install not run if tool is uninstalled ([`5547b88`](https://github.com/yanga-project/yanga/commit/5547b88519b300073eb33720aede0d4c128adcf1))

## v0.8.0 (2023-09-29)

### Features

- Add dummy yanga build stage ([`e65a7cb`](https://github.com/yanga-project/yanga/commit/e65a7cb4d7ed67a3c6fd9e145b022b81c2afe59d))

## v0.7.0 (2023-07-09)

### Features

- Automatically build yanga projects ([`3101666`](https://github.com/yanga-project/yanga/commit/31016662f543a00198184818e700fb70261d1739))

## v0.6.0 (2023-07-09)

### Bug fixes

- Bootstrap for unix fails running commands ([`8085a05`](https://github.com/yanga-project/yanga/commit/8085a05d8d57cf1de538105f5b31a7dd565c2c73))

### Features

- Update bootstrap to only run if required ([`55f1c8f`](https://github.com/yanga-project/yanga/commit/55f1c8fe60933be86c053ea7370d9ae2074a84fd))
- Update pipeline to use the executor ([`eb3f676`](https://github.com/yanga-project/yanga/commit/eb3f676ac83d7a2ec0f8e8d6be78127ae4fef6c7))
- Implement runnable executor ([`7462d63`](https://github.com/yanga-project/yanga/commit/7462d63e15f016c1d8967c9c42f311247945e3a7))
- Support build.py for linux ([`26b0542`](https://github.com/yanga-project/yanga/commit/26b05428e870b6d0504933f4877ed0e854542f18))

## v0.5.0 (2023-07-05)

### Features

- Support user pipeline stages ([`4cd2d2c`](https://github.com/yanga-project/yanga/commit/4cd2d2c61e992252befc523508efe6a2c0e4b3cd))

## v0.4.0 (2023-07-05)

### Features

- Add --version option ([`4b1eeee`](https://github.com/yanga-project/yanga/commit/4b1eeee37168b47037c08aa48a2b24e45da2f5d6))
- Add install command for scoop ([`045b767`](https://github.com/yanga-project/yanga/commit/045b767e7c4e258e8bf21947510f05841bb4dcc3))

## v0.3.0 (2023-07-03)

### Features

- Scoop apps installer wrapper ([`2221c36`](https://github.com/yanga-project/yanga/commit/2221c360dd129102678173e108befedb0bfde9fc))

## v0.2.3 (2023-07-03)

### Bug fixes

- Init command fails because dir exists ([`93ddefb`](https://github.com/yanga-project/yanga/commit/93ddefb398a4d4cef6b83c6ac68ac923e2d5f221))

## v0.2.2 (2023-07-03)

### Bug fixes

- Init command fails because dir is not empty ([`fb57839`](https://github.com/yanga-project/yanga/commit/fb57839d5a2c60e4a87305f408012aaba1d6b3ae))

### Documentation

- Collect some ideas to implement next ([`be266b0`](https://github.com/yanga-project/yanga/commit/be266b07e309a12e9a0da1dce13f4856310e8aa3))

## v0.2.1 (2023-07-02)

### Bug fixes

- Python fails because of missing bucket ([`924dcb1`](https://github.com/yanga-project/yanga/commit/924dcb11e53e354501832a3bc809a1fe2fcc8a52))

## v0.2.0 (2023-07-02)

### Features

- Update bootstrap script ([`e06745b`](https://github.com/yanga-project/yanga/commit/e06745bf45a93ce5cad1c18b98c0a9043f5f1b73))
- Support for python 3.10 ([`ea18623`](https://github.com/yanga-project/yanga/commit/ea18623c50c7fd35fd576dd6577de49a63a79900))
- Support windows and python >=3.11 ([`1cee197`](https://github.com/yanga-project/yanga/commit/1cee197ce69652c065af99b084e6648125c2d7a5))
- Collect installed scoop apps ([`f90e73a`](https://github.com/yanga-project/yanga/commit/f90e73ab142ecac9b8ce1aa1a20601cce89bef5f))
- Build script installs python dependencies ([`fa94d4e`](https://github.com/yanga-project/yanga/commit/fa94d4e4c02892241aedc08ff1fe3b3c75f134ee))
- Add init command with only build scripts ([`7f4a145`](https://github.com/yanga-project/yanga/commit/7f4a145538376bc44e4b397df480c2f8983cbaad))

### Bug fixes

- Build.py test wrongly installs poetry deps ([`61fe118`](https://github.com/yanga-project/yanga/commit/61fe1180548ff89a751e0fcd493f9505619f27e1))

## v0.1.0 (2023-06-06)

### Features

- Add command line parser ([`7a6c1bd`](https://github.com/yanga-project/yanga/commit/7a6c1bd696f03c02ed0686b45ad6000ead827c1a))
- Add variant configuration ([`d0a823c`](https://github.com/yanga-project/yanga/commit/d0a823c27d18582f407f4c18832c17123edfb3a7))
- Add logger based on loguru ([`251ffb3`](https://github.com/yanga-project/yanga/commit/251ffb3c6e51dc0b6288804253bb03e446c2335e))

### Bug fixes

- Readthedocs build is failing ([`8b55345`](https://github.com/yanga-project/yanga/commit/8b55345ea79e1336a80296330828cf7b53dcb25b))

### Documentation

- Add requirements tests traceability ([`6fe3d22`](https://github.com/yanga-project/yanga/commit/6fe3d2208105b1084ae725eabd8812b5883499af))
- Brainstorming artifacts ([`5ccd062`](https://github.com/yanga-project/yanga/commit/5ccd06265e4c550e94219ef1794bff9eb2b8fc92))
