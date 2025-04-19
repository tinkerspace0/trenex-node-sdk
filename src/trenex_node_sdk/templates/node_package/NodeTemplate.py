from trenex_node_sdk.node.node_base import Node
from trenex_node_sdk.node.node_param import Param

class NodeTemplate(Node):
    """
    A generated node template for category `category`.
    """
    def __init__(self, name=None):
        super().__init__(name)
        # Example static parameter:
        # self.get_static_params().add_param(
        #     Param("threshold", float, default_value=0.5,
        #           description="Example threshold parameter")
        # )

    def update_io(self):
        """
        Define inputs & outputs here.
        """
        inp, out = self.get_io()
        # inp.create_io("in1", dtype=float)
        # out.create_io("out1", dtype=float)
        pass

    def process(self):
        """
        Implement processing logic here.
        """
        # data = self.get_in_io().in1.read()
        # result = ...
        # self.get_out_io().out1.write(result)
        pass